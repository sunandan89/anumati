"""Channel gateway (spec section 3): outbound messages through a configured Channel Provider, logged as
stock Communication records.

Rules: only approved Message Templates are sent (DLT in India); the phone number is read from the
encrypted field at send time and never written to the Communication (only its salted hash is); message
bodies carry codes and purpose names, never the principal's name."""

import frappe
from frappe.utils import formatdate, now_datetime

from anumati import pii

PROVIDERS = {"MSG91": "anumati.channels.msg91", "Twilio": "anumati.channels.twilio"}


class ChannelError(frappe.ValidationError):
	pass


def provider_for(provider_type="SMS"):
	name = frappe.db.get_value("Channel Provider", {"provider_type": provider_type, "enabled": 1}, "name")
	return frappe.get_doc("Channel Provider", name) if name else None


def template_for(event: str, channel: str, language: str | None):
	for lang in dict.fromkeys([language, frappe.db.get_single_value("System Settings", "language"), "en"]):
		if not lang:
			continue
		name = frappe.db.get_value("Message Template",
		                           {"template_event": event, "channel": channel, "language": lang, "approved": 1})
		if name:
			return frappe.get_doc("Message Template", name)
	return None


def _send_templated(provider_type: str, channel: str, principal: str, event: str, context: dict, reference=None,
                    reference_doctype="Consent Event") -> str | None:
	"""Send one approved template to a principal on a channel. Returns the Communication name, or None if
	not sendable (no provider, no approved template, no phone). Never raises for a missing setup: capture
	must not fail because a receipt could not be sent."""
	provider = provider_for(provider_type)
	doc = frappe.get_doc("Data Principal", principal)
	phone = doc.get_password("phone", raise_exception=False)
	# WhatsApp falls back to the approved SMS wording when no WhatsApp template exists yet.
	template = template_for(event, channel, doc.preferred_language) or (
		template_for(event, "sms", doc.preferred_language) if channel == "whatsapp" else None)
	if not (provider and template and phone):
		return None
	body = frappe.render_template(template.body, context)
	adapter = frappe.get_module(PROVIDERS.get(provider.provider, "anumati.channels.msg91"))
	status, message_id = "Sent", None
	try:
		message_id = adapter.send(provider, pii.normalise_phone(phone), template, context)
	except Exception:
		status = "Error"
		frappe.log_error(title=f"Anumati {channel} send failed ({event})", message=f"provider={provider.name} template={template.name}")
	return log(provider, "Sent", body, pii.phone_hash(phone), template=template.name, status=status,
	           message_id=message_id, reference=reference, reference_doctype=reference_doctype, channel=channel)


def send_sms(principal: str, event: str, context: dict, reference=None, reference_doctype="Consent Event") -> str | None:
	return _send_templated("SMS", "sms", principal, event, context, reference, reference_doctype)


def send_whatsapp(principal: str, event: str, context: dict, reference=None, reference_doctype="Consent Event") -> str | None:
	return _send_templated("WhatsApp", "whatsapp", principal, event, context, reference, reference_doctype)


SENDERS = {"sms": "send_sms", "whatsapp": "send_whatsapp"}  # email joins in Phase 2g


def send(principal: str, event: str, context: dict, channel=None, reference=None, reference_doctype="Consent Event"):
	"""Send a templated message on the channel the principal used, falling back to SMS. Returns the
	Communication name or None when nothing could be sent (never raises for a missing setup)."""
	for ch in dict.fromkeys([channel, "sms"]):
		if ch in SENDERS:
			comm = globals()[SENDERS[ch]](principal, event, context, reference=reference, reference_doctype=reference_doctype)
			if comm:
				return comm
	return None


def log(provider, direction, body, phone_hash, template=None, status=None, message_id=None, reference=None,
        channel="sms", reference_doctype="Consent Event"):
	"""A stock Communication with the Anumati custom fields; phone_no is deliberately left empty.
	`reference` links it to a Consent Event (default) or to a Rights Request thread."""
	if not (reference and frappe.db.exists(reference_doctype, reference)):
		reference = None
	event = reference if reference_doctype == "Consent Event" else None
	comm = frappe.get_doc({
		"doctype": "Communication",
		"communication_type": "Communication",
		"communication_medium": {"sms": "SMS", "whatsapp": "Chat", "ivr": "Phone", "missed_call": "Phone"}.get(channel, "Other"),
		"sent_or_received": direction,
		"subject": f"{channel.upper()} {direction.lower()}",
		"content": body,
		"delivery_status": status,
		"message_id": message_id,
		"communication_date": now_datetime(),
		"anumati_channel": channel,
		"anumati_sender_hash": phone_hash,
		"anumati_provider": provider.name if provider else None,
		"anumati_message_template": template,
		"anumati_consent_event": event,
		"reference_doctype": reference_doctype if reference else None,
		"reference_name": reference,
	})
	comm.flags.ignore_permissions = True
	comm.insert()
	return comm.name


def event_context(event) -> dict:
	import json

	programme = frappe.get_cached_doc("Programme", event.programme)
	codes = json.loads(event.purposes_granted or "[]") or json.loads(event.purposes_denied or "[]")
	titles = [frappe.db.get_value("Purpose", f"{event.programme}-{c}", "purpose_title") or c for c in codes]
	return {"code": event.short_code, "programme": programme.programme_name, "purposes": ", ".join(titles),
	        "purpose_list": titles, "date": formatdate(event.server_time), "action": event.action}


def on_consent_event(event: str):
	"""Background job after a consent event commits: receipt, withdrawal confirmation, or deferred
	confirmation request (spec sections 5 and 6)."""
	doc = frappe.get_doc("Consent Event", event)
	if not frappe.db.get_value("Programme", doc.programme, "sms_receipts"):
		return
	context = event_context(doc)
	if doc.action == "withdraw":
		send_sms(doc.principal, "withdrawal_confirmation", context, reference=doc.name)
	elif doc.verification_method == "deferred":
		comm = send_sms(doc.principal, "deferred_confirmation", context, reference=doc.name)
		if comm:
			frappe.get_doc({"doctype": "Verification Attempt", "consent_event": doc.name, "verification_method": "deferred",
			                "channel": "sms", "sent_at": now_datetime(), "result": "pending",
			                "response": comm}).insert(ignore_permissions=True)
	else:
		send_sms(doc.principal, "receipt", context, reference=doc.name)
