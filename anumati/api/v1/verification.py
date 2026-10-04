"""Server OTP (spec section 5, "Online" rung): /api/v2/method/anumati.api.v1.verification.<name>

The server makes the code and sends it straight to the person's phone (or their guardian's) through the
SMS provider, so the field worker never sees it; the person reads it back. The code lives in Redis with a
TTL (never in the database or in logs); only its hash is kept on the Verification Attempt. Five wrong
tries lock the attempt, and a consent can be sent at most MAX_SENDS codes in TTL_SECONDS."""

import hashlib
import hmac
import secrets
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import now_datetime

from anumati import channels, enforcement
from anumati.api.v1.principal import mask_phone

TTL_SECONDS = 600
MAX_TRIES = 5
MAX_SENDS = 3
STAFF = {"Anumati Admin", "Anumati DPO", "Anumati Operator", "System Manager"}


def _key(event):
	return f"anumati:otp:{event}"


def _hash(event, code):
	return hashlib.sha256(f"{event}:{code}".encode()).hexdigest()


def _event_for_caller(consent_id):
	"""The worker who captured the consent, or staff, may verify it; nobody else."""
	frappe.has_permission("Consent Event", "create", throw=True)
	event = frappe.get_doc("Consent Event", consent_id)
	if event.captured_by != frappe.session.user and not STAFF & set(frappe.get_roles()):
		raise frappe.PermissionError
	return event


@frappe.whitelist(methods=["POST"])
def send_otp(consent_id):
	event = _event_for_caller(consent_id)
	recent = frappe.db.count("Verification Attempt", {
		"consent_event": event.name, "verification_method": "server_otp",
		"sent_at": (">", now_datetime() - timedelta(seconds=TTL_SECONDS))})
	if recent >= MAX_SENDS:
		frappe.throw(_("Too many codes sent for this consent; try again in 10 minutes"))
	code = f"{secrets.randbelow(10**6):06d}"
	comm = channels.send_sms(event.principal, "otp", {**channels.event_context(event), "otp": code}, reference=event.name)
	sent = bool(comm) and frappe.db.get_value("Communication", comm, "delivery_status") != "Error"
	if not sent:
		# Not set up (no provider, template or phone) or the provider refused: nothing to check against.
		return {"sent": False, "reason": "not_sent" if comm else "not_set_up"}
	frappe.cache.set_value(_key(event.name), {"hash": _hash(event.name, code), "tries": 0}, expires_in_sec=TTL_SECONDS)
	attempt = frappe.get_doc({"doctype": "Verification Attempt", "consent_event": event.name,
	                          "verification_method": "server_otp", "channel": "sms", "sent_at": now_datetime(),
	                          "code_hash": _hash(event.name, code), "result": "pending", "response": comm})
	attempt.insert(ignore_permissions=True)
	phone = channels.contact_phone(frappe.get_doc("Data Principal", event.principal)) or ""
	return {"attempt": attempt.name, "sent": True, "expires_in": TTL_SECONDS, "to": mask_phone(phone)}


@frappe.whitelist(methods=["POST"])
def verify_otp(consent_id, code):
	_event_for_caller(consent_id)
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
