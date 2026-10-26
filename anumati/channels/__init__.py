"""Channel gateway (spec section 3): outbound messages through a configured Channel Provider, logged as
stock Communication records.

Rules: only approved Message Templates are sent (DLT in India); the phone number is read from the
encrypted field at send time and never written to the Communication (only its salted hash is); message
bodies carry codes and purpose names, never the principal's name."""

import frappe
from frappe.utils import formatdate, get_url, now_datetime

from anumati import pii

PROVIDERS = {"MSG91": "anumati.channels.msg91"}


class ChannelError(frappe.ValidationError):
	pass


def provider_for(provider_type="SMS"):
	name = frappe.db.get_value("Anumati Channel Provider", {"provider_type": provider_type, "enabled": 1}, "name")
	return frappe.get_doc("Anumati Channel Provider", name) if name else None


def template_for(event: str, channel: str, language: str | None):
	for lang in dict.fromkeys([language, frappe.db.get_single_value("System Settings", "language"), "en"]):
		if not lang:
			continue
		name = frappe.db.get_value("Anumati Message Template",
		                           {"template_event": event, "channel": channel, "language": lang, "approved": 1})
		if name:
			return frappe.get_doc("Anumati Message Template", name)
	return None


def can_send_codes(language: str | None = None) -> bool:
	"""The server can text one-time codes: an enabled SMS account with a key, and an approved OTP template.
	When it can't (e.g. MSG91 not set up yet), the field app sends codes from the worker's phone with the
	voice 'haan' instead."""
	provider = provider_for("SMS")
	if not provider or not template_for("otp", "sms", language):
		return False
	return bool(provider.get_password("api_key", raise_exception=False) or frappe.conf.get("msg91_auth_key"))


def contact_phone(doc) -> str | None:
	"""The number messages about this person go to: for a child, or an adult with a lawful guardian, the
	guardian's (from their latest Guardian Link) because the guardian decided; otherwise their own."""
	own = doc.get_password("phone", raise_exception=False)
	guarded = (doc.is_minor and not doc.get("renewal_due")) or doc.pwd_guarded
	if guarded or not own:
		guardian = frappe.db.get_value("Anumati Guardian Link", {"principal": doc.name}, "guardian", order_by="creation desc")
		if guardian:
			theirs = frappe.get_doc("Anumati Data Principal", guardian).get_password("phone", raise_exception=False)
			if theirs:
				return theirs
	return own


def send_sms(principal: str, event: str, context: dict, reference=None, link=None) -> str | None:
	"""Send one templated SMS to a principal. Returns the Communication name, or None if not sendable
	(no provider, no approved template, no phone). Never raises for a missing setup: capture must not
	fail because a receipt could not be sent."""
	provider = provider_for("SMS")
	doc = frappe.get_doc("Anumati Data Principal", principal)
	phone = contact_phone(doc)
	template = template_for(event, "sms", doc.preferred_language)
	if not (provider and template and phone):
		return None
	# The log keeps what was said, never a one-time code.
	body = frappe.render_template(template.body, {**context, **({"otp": "******"} if context.get("otp") else {})}, restrict_globals=True)  # staff-written SMS template, globals restricted; nosemgrep
	adapter = frappe.get_module(PROVIDERS.get(provider.provider, "anumati.channels.msg91"))
	status, message_id = "Sent", None
	try:
		message_id = adapter.send(provider, pii.normalise_phone(phone), template, context)
	except Exception:
		status = "Error"
		frappe.log_error(title=f"Anumati SMS send failed ({event})", message=f"provider={provider.name} template={template.name}")
	return log(provider, "Sent", body, pii.phone_hash(phone), template=template.name, status=status,
	           message_id=message_id, reference=reference, link=link)


def log(provider, direction, body, phone_hash, template=None, status=None, message_id=None, reference=None,
        channel="sms", link=None, delivery=None):
	"""A stock Communication with the Anumati custom fields; phone_no is deliberately left empty. `link` is a
	(doctype, name) the message is about when it isn't a Consent Event (e.g. a Breach Incident)."""
	is_event = bool(reference and frappe.db.exists("Anumati Consent Event", reference))
	ref_doctype, ref_name = ("Anumati Consent Event", reference) if is_event else (link or (None, None))
	comm = frappe.get_doc({
		"doctype": "Communication",
		"communication_type": "Communication",
		"communication_medium": "SMS" if channel == "sms" else "Other",
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
		"anumati_consent_event": reference if is_event else None,
		"anumati_delivery": delivery,
		"reference_doctype": ref_doctype,
		"reference_name": ref_name,
	})
	comm.flags.ignore_permissions = True
	comm.insert()
	return comm.name


def event_context(event) -> dict:
	import json

	programme = frappe.get_cached_doc("Anumati Programme", event.programme)
	codes = json.loads(event.purposes_granted or "[]") or json.loads(event.purposes_denied or "[]")
	titles = [frappe.db.get_value("Anumati Purpose", f"{event.programme}-{c}", "purpose_title") or c for c in codes]
	return {"code": event.short_code, "programme": programme.programme_name, "purposes": ", ".join(titles),
	        "purpose_list": titles, "date": formatdate(event.server_time), "action": event.action,
	        "link": get_url("/my-consent")}


def on_consent_event(event: str):
	"""Background job after a consent event commits: receipt, withdrawal confirmation, or deferred
	confirmation request (spec sections 5 and 6)."""
	doc = frappe.get_doc("Anumati Consent Event", event)
	if not frappe.db.get_value("Anumati Programme", doc.programme, "sms_receipts"):
		return
	context = event_context(doc)
	if doc.action == "withdraw":
		send_sms(doc.principal, "withdrawal_confirmation", context, reference=doc.name)
	elif doc.verification_method == "deferred":
		comm = send_sms(doc.principal, "deferred_confirmation", context, reference=doc.name)
		if comm:
			frappe.get_doc({"doctype": "Anumati Verification Attempt", "consent_event": doc.name, "verification_method": "deferred",
			                "channel": "sms", "sent_at": now_datetime(), "result": "pending",
			                "response": comm}).insert(ignore_permissions=True)
	else:
		send_sms(doc.principal, "receipt", context, reference=doc.name)
