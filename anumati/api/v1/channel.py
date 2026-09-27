"""Inbound channel callbacks (spec sections 6 and 8): /api/method/anumati.api.v1.channel.<name>

Open to guests because SMS gateways call them, so each call must carry the Channel Provider's inbound
secret (compared in constant time) and is rate-limited. Nothing here echoes personal data back.

SMS keywords (case-insensitive, Devanagari digits accepted):
  STOP            withdraw every optional purpose (if the number maps to exactly one person)
  STOP <code>     withdraw the consent with that receipt code
  STOP <n>        withdraw purpose number n from the latest receipt
  DATA            access request      HELP  call-back request (grievance)
Anything ambiguous becomes a Rights Request for a person to resolve; the SLA clock starts now."""

import hmac
import json
import re
import uuid

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime

from anumati import channels, inbox, pii
from anumati.api.v1 import consent

DEVANAGARI = str.maketrans("०१२३४५६७८९", "0123456789")


def _provider(provider, token):
	doc = frappe.get_doc("Channel Provider", provider) if provider and frappe.db.exists("Channel Provider", provider) else None
	secret = doc.get_password("webhook_secret", raise_exception=False) if doc else None
	if not (doc and doc.enabled and secret and token and hmac.compare_digest(str(secret), str(token))):
		raise frappe.PermissionError
	return doc


def _request(request_type, channel, phone_hash, text, status=None, principal=None):
	req = frappe.get_doc({"doctype": "Rights Request", "request_type": request_type, "channel": channel,
	                      "sender_hash": phone_hash, "raw_payload": text, "matched_principal": principal,
	                      **({"status": status} if status else {})})
	req.flags.ignore_permissions = True
	req.insert()
	return req


def _latest_grant(principal):
	return frappe.db.get_value("Consent Event", {"principal": principal, "action": ("in", ["grant", "renew"])},
	                           ["name", "programme", "purposes_granted"], order_by="chain_seq desc", as_dict=True)


def handle_sms(provider, sender, text):
	"""Process one inbound SMS; returns a short machine-readable outcome."""
	phone_hash = pii.phone_hash(sender)
	channels.log(provider, "Received", text, phone_hash)
	words = (text or "").translate(DEVANAGARI).strip().split()
	keyword = words[0].upper() if words else ""
	arg = words[1] if len(words) > 1 else None

	if keyword == "DATA":
		return {"outcome": "request", "request": _request("access", "sms", phone_hash, text).name}
	if keyword == "HELP":
		return {"outcome": "request", "request": _request("grievance", "sms", phone_hash, text).name}
	if keyword != "STOP":
		return {"outcome": "request", "request": _request("grievance", "sms", phone_hash, text).name}

	principal, purposes, programme = None, None, None
	if arg and not arg.isdigit():
		principal, programme = inbox.event_for_short_code(arg)
	else:
		found = inbox.principals_for_phone_hash(phone_hash)
		if len(found) == 1:
			principal = found[0].name
	req = _request("withdrawal", "sms", phone_hash, text, principal=principal)
	if not principal:
		return {"outcome": "unmatched", "request": req.name}

	grant = _latest_grant(principal)
	if arg and arg.isdigit() and grant:
		codes = json.loads(grant.purposes_granted or "[]")
		n = int(arg)
		if not 1 <= n <= len(codes):
			return {"outcome": "request", "request": req.name}
		purposes, programme = [codes[n - 1]], grant.programme
	programmes = [programme] if programme else sorted(
		{p.programme for p in frappe.get_all("Consent State", {"principal": principal, "status": "granted"}, ["programme"])})
	artefacts = [consent.withdraw_for(principal, prog, "sms", f"sms-{req.name}-{prog}", purposes)
	             for prog in programmes]
	req.reload()
	req.update({"status": "Closed", "linked_event": artefacts[0]["consent_id"] if artefacts else None,
	            "resolution": "Withdrawn by SMS: " + ", ".join(a["short_code"] for a in artefacts)})
	req.flags.ignore_permissions = True
	req.save()
	return {"outcome": "withdrawn", "request": req.name, "events": len(artefacts)}


def _sender(kwargs):
	for key in ("sender", "from", "mobile", "msisdn", "caller", "From", "CallFrom"):
		if kwargs.get(key):
			return kwargs[key]
	return None


def _text(kwargs):
	for key in ("message", "text", "content", "sms", "Body"):
		if kwargs.get(key) is not None:
			return kwargs[key]
	return ""


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
@rate_limit(limit=600, seconds=60)
def inbound_sms(provider=None, token=None, **kwargs):
	prov = _provider(provider, token)
	sender = _sender(kwargs)
	if not sender:
		frappe.throw("sender missing")
	return handle_sms(prov, sender, _text(kwargs))


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
@rate_limit(limit=600, seconds=60)
def missed_call(provider=None, token=None, **kwargs):
	"""A missed call is a withdrawal request; it is confirmed by a call-back or SMS, never auto-applied."""
	prov = _provider(provider, token)
	sender = _sender(kwargs)
	if not sender:
		frappe.throw("caller missing")
	phone_hash = pii.phone_hash(sender)
	channels.log(prov, "Received", "Missed call", phone_hash, channel="missed_call")
	found = inbox.principals_for_phone_hash(phone_hash)
	req = _request("withdrawal", "missed_call", phone_hash, "Missed call",
	               principal=found[0].name if len(found) == 1 else None)
	return {"outcome": "request", "request": req.name}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
@rate_limit(limit=1200, seconds=60)
def delivery_report(provider=None, token=None, request_id=None, status=None, **kwargs):
	"""Delivery receipts: a delivered deferred-confirmation SMS confirms that consent (spec section 5)."""
	_provider(provider, token)
	comm = frappe.db.get_value("Communication", {"message_id": request_id}, "name") if request_id else None
	if not comm:
		return {"outcome": "unknown"}
	delivered = str(status or "").lower() in ("1", "delivered", "success", "delivrd")
	for att in frappe.get_all("Verification Attempt", {"response": comm, "result": "pending"}, ["name", "consent_event"]):
		if delivered:
			frappe.db.set_value("Verification Attempt", att.name, {"result": "confirmed", "delivered_at": now_datetime()})
			from anumati import enforcement

			enforcement.set_verification(att.consent_event, "confirmed")
	return {"outcome": "delivered" if delivered else "noted"}
