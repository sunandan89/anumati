"""Server OTP (spec section 5, "Online" rung): /api/v2/method/anumati.api.v1.verification.<name>

The code lives in Redis with a TTL (never in memory, never in the database); only its hash is kept on
the Verification Attempt. Five wrong tries lock the attempt."""

import hashlib
import hmac
import secrets

import frappe
from frappe import _
from frappe.utils import now_datetime

from anumati import channels, enforcement

TTL_SECONDS = 600
MAX_TRIES = 5


def _key(event):
	return f"anumati:otp:{event}"


def _hash(event, code):
	return hashlib.sha256(f"{event}:{code}".encode()).hexdigest()


@frappe.whitelist(methods=["POST"])
def send_otp(consent_id):
	frappe.has_permission("Consent Event", "create", throw=True)
	event = frappe.get_doc("Consent Event", consent_id)
	code = f"{secrets.randbelow(10**6):06d}"
	frappe.cache.set_value(_key(event.name), {"hash": _hash(event.name, code), "tries": 0}, expires_in_sec=TTL_SECONDS)
	comm = channels.send_sms(event.principal, "otp", {**channels.event_context(event), "otp": code}, reference=event.name)
	attempt = frappe.get_doc({"doctype": "Verification Attempt", "consent_event": event.name,
	                          "verification_method": "server_otp", "channel": "sms", "sent_at": now_datetime(),
	                          "code_hash": _hash(event.name, code), "result": "pending", "response": comm})
	attempt.insert(ignore_permissions=True)
	return {"attempt": attempt.name, "sent": bool(comm), "expires_in": TTL_SECONDS}


@frappe.whitelist(methods=["POST"])
def verify_otp(consent_id, code):
	frappe.has_permission("Consent Event", "create", throw=True)
	stored = frappe.cache.get_value(_key(consent_id))
	attempt = frappe.db.get_value("Verification Attempt",
	                              {"consent_event": consent_id, "verification_method": "server_otp", "result": "pending"},
	                              order_by="creation desc")
	if not stored or not attempt:
		frappe.throw(_("No active code; send a new one"))
	if stored["tries"] >= MAX_TRIES:
		frappe.db.set_value("Verification Attempt", attempt, "result", "failed")
		frappe.throw(_("Too many attempts; send a new code"))
	if not hmac.compare_digest(stored["hash"], _hash(consent_id, str(code).strip())):
		stored["tries"] += 1
		frappe.cache.set_value(_key(consent_id), stored, expires_in_sec=TTL_SECONDS)
		return {"confirmed": False, "tries_left": MAX_TRIES - stored["tries"]}
	frappe.cache.delete_value(_key(consent_id))
	frappe.db.set_value("Verification Attempt", attempt, {"result": "confirmed", "delivered_at": now_datetime()})
	enforcement.set_verification(consent_id, "confirmed")
	return {"confirmed": True}
