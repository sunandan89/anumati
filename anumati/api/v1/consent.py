"""Consent API, v1. Served at /api/v2/method/anumati.api.v1.consent.<name> (and /api/method/...).

Authorisation uses stock Frappe permissions on the API user's roles (spec gap 10, key scopes):
  capture  = create on Consent Event   (record, withdraw)
  check    = read on Consent State     (check, state)
Every write is idempotent on the client-generated event_uuid (spec section 8)."""

import json

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime

from anumati import enforcement
from anumati.api import schema
from anumati.ledger import keystore, signing

CAPTURE_FIELDS = (
	"notice", "language", "capture_mode", "channel", "device_id", "device_time", "ip_address", "gps",
	"verification_method", "witness", "evidence", "guardian_link", "source_system",
	"notice_delivery", "notice_completed",
)
CLIENT_VERIFICATION = ("recorded", "confirmed", "evidence_only")


class ConsentRequestError(frappe.ValidationError):
	pass


def _parse(value):
	if isinstance(value, str):
		value = json.loads(value)
	return frappe._dict(value or {})


def _principal(principal_ref: str) -> str:
	name = frappe.db.get_value("Data Principal", {"principal_ref": principal_ref})
	if not name:
		frappe.throw(_("Unknown principal_ref {0}; call principal.upsert first").format(principal_ref), ConsentRequestError)
	return name


def _programme(programme: str):
	if not programme or not frappe.db.exists("Programme", programme):
		frappe.throw(_("Unknown programme {0}").format(programme), ConsentRequestError)
	return programme


def _artefact(event) -> dict:
	"""The signed receipt returned to capture clients. Carries no personal data."""
	return {
		"consent_id": event.name,
		"short_code": event.short_code or short_code(event.event_uuid),
		"event_uuid": event.event_uuid,
		"action": event.action,
		"chain_seq": event.chain_seq,
		"hash": event.hash,
		"signature": event.signature,
		"key_id": event.key_id,
		"server_time": event.server_time,
		"verification_status": event.verification_status,
	}


def short_code(event_uuid: str) -> str:
	"""The code printed on receipts and slips, e.g. AN-7K2Q9C: the first 30 bits of sha256(event_uuid) in
	base32. It depends only on the event_uuid the capture device generates, so an offline field app can
	write the same code on the slip before the event reaches the server. Codes are short and can collide;
	lookups resolve a collision by the sender's phone hash or leave it for a person (inbox)."""
	import base64
	import hashlib

	return "AN-" + base64.b32encode(hashlib.sha256(event_uuid.encode()).digest()[:5]).decode()[:6]


def _existing(event_uuid: str):
	if frappe.db.exists("Consent Event", event_uuid):
		return _artefact(frappe.get_doc("Consent Event", event_uuid))
	return None


def _check_purposes(programme: str, principal: str, granted: list, denied: list):
	if set(granted) & set(denied):
		frappe.throw(_("A purpose cannot be both granted and denied"), ConsentRequestError)
	is_minor = frappe.db.get_value("Data Principal", principal, "is_minor")
	for code in granted + denied:
		row = frappe.db.get_value("Purpose", enforcement.purpose_name(programme, code), ["child_allowed"], as_dict=True)
		if not row:
			frappe.throw(_("Unknown purpose {0} for programme {1}").format(code, programme), ConsentRequestError)
		if is_minor and code in granted and not row.child_allowed:
			frappe.throw(_("Purpose {0} is not allowed for minors").format(code), ConsentRequestError)


def _insert(values: dict) -> dict:
	doc = frappe.get_doc({"doctype": "Consent Event", **values})
	frappe.db.savepoint("anumati_record")
	try:
		doc.insert()
	except frappe.DuplicateEntryError:
		# Same event_uuid synced twice at once: return the one that won.
		frappe.db.rollback(save_point="anumati_record")
		return _existing(values["event_uuid"])
	return _artefact(doc)


@frappe.whitelist(methods=["POST"])
def record(event):
	"""Record a grant, refusal or renewal. Returns the signed artefact; replays return the original."""
	event = _parse(event)
	frappe.has_permission("Consent Event", "create", throw=True)
	schema.validate("ConsentRecord", {k: v for k, v in event.items() if v is not None})
	if not event.event_uuid:
		frappe.throw(_("event_uuid is required"), ConsentRequestError)
	if (existing := _existing(event.event_uuid)):
		return existing
	action = event.action or "grant"
	if action not in ("grant", "refuse", "renew"):
		frappe.throw(_("Use consent.withdraw to withdraw"), ConsentRequestError)

	principal = _principal(event.principal_ref)
	programme = _programme(event.programme)
	granted, denied = list(event.purposes_granted or []), list(event.purposes_denied or [])
	if action == "refuse":
		granted, denied = [], denied or granted
	_check_purposes(programme, principal, granted, denied)

	if frappe.db.get_value("Data Principal", principal, "is_minor") and not event.guardian_link:
		frappe.throw(_("A minor's consent needs a verified guardian_link (spec C1)"), ConsentRequestError)
	values = {k: event.get(k) for k in CAPTURE_FIELDS if event.get(k) not in (None, "")}
	if values.get("notice"):
		notice = frappe.db.get_value("Notice Template", values["notice"], ["programme", "version", "docstatus"], as_dict=True)
		if not notice or notice.programme != programme or notice.docstatus != 1:
			frappe.throw(_("notice must be a published notice of this programme"), ConsentRequestError)
		values["notice_version"] = notice.version
	status = event.verification_status or ("evidence_only" if event.verification_method == "evidence_only" else "recorded")
	if status not in CLIENT_VERIFICATION:
		frappe.throw(_("verification_status must be one of {0}").format(", ".join(CLIENT_VERIFICATION)), ConsentRequestError)

	return _insert(
		{**values, "event_uuid": event.event_uuid, "action": action, "principal": principal, "programme": programme,
		 "purposes_granted": granted, "purposes_denied": denied, "verification_status": status,
		 "captured_by": frappe.session.user}
	)


@frappe.whitelist(methods=["POST"])
def withdraw(principal_ref, programme, channel, event_uuid, purposes=None, **extra):
	"""Withdraw consent. Default scope = every optional purpose currently granted (spec section 6)."""
	frappe.has_permission("Consent Event", "create", throw=True)
	payload = {"principal_ref": principal_ref, "programme": programme, "channel": channel, "event_uuid": event_uuid,
	           **({"purposes": json.loads(purposes) if isinstance(purposes, str) else purposes} if purposes else {}),
	           **{k: v for k, v in extra.items() if k not in ("cmd", "data") and v is not None}}
	schema.validate("ConsentWithdraw", payload)
	return withdraw_for(_principal(principal_ref), programme, channel, event_uuid, purposes, **extra)


def withdraw_for(principal, programme, channel, event_uuid, purposes=None, **extra):
	"""Withdrawal without the capture-permission check. Callers must authorise first (the API above, or a
	rights request the operator is allowed to work)."""
	if (existing := _existing(event_uuid)):
		return existing
	programme = _programme(programme)
	purposes = json.loads(purposes) if isinstance(purposes, str) else purposes
	if not purposes:
		states = enforcement.states_for(principal)
		prefix = f"{programme}-"
		purposes = [
			p[len(prefix):] for p, s in states.items()
			if p.startswith(prefix) and s["status"] == "granted" and not frappe.db.get_value("Purpose", p, "essential")
		]
	_check_purposes(programme, principal, [], list(purposes))
	values = {k: extra.get(k) for k in CAPTURE_FIELDS if extra.get(k) not in (None, "")}
	values.update(
		{"event_uuid": event_uuid, "action": "withdraw", "principal": principal, "programme": programme,
		 "channel": channel, "purposes_granted": [], "purposes_denied": list(purposes),
		 "verification_status": "recorded", "captured_by": frappe.session.user}
	)
	doc = frappe.get_doc({"doctype": "Consent Event", **values})
	doc.flags.ignore_permissions = True
	frappe.db.savepoint("anumati_withdraw")
	try:
		doc.insert()
	except frappe.DuplicateEntryError:
		frappe.db.rollback(save_point="anumati_withdraw")
		return _existing(event_uuid)
	return _artefact(doc)


def _source_system(user: str):
	return frappe.cache.get_value(
		f"anumati:source_system:{user}", generator=lambda: frappe.db.get_value("Source System", {"api_user": user})
	)


@frappe.whitelist(methods=["GET", "POST"])
def check(principal_ref, purpose, programme=None):
	"""Enforcement gate: may this purpose be processed for this principal right now? Served from cache."""
	frappe.has_permission("Consent State", "read", throw=True)
	purpose_name = enforcement.purpose_name(programme, purpose) if programme else purpose
	principal = frappe.cache.get_value(
		f"anumati:principal:{principal_ref}",
		generator=lambda: frappe.db.get_value("Data Principal", {"principal_ref": principal_ref}),
	)
	state = enforcement.states_for(principal).get(purpose_name) if principal else None
	status = state["status"] if state else ("unknown_principal" if not principal else "not_asked")
	allow = status == "granted"
	if allow and state.get("verification") not in ("confirmed", "evidence_only"):
		programme_name = frappe.get_cached_value("Purpose", purpose_name, "programme")
		minor = frappe.get_cached_value("Data Principal", principal, "is_minor")
		before_confirm = frappe.get_cached_value("Programme", programme_name, "allow_processing_before_confirm")
		if minor or not before_confirm:
			allow, status = False, "awaiting_confirmation"
	checked_at = now_datetime()
	if principal:
		from frappe.deferred_insert import deferred_insert

		deferred_insert("System Usage Log", [{
			"source_system": _source_system(frappe.session.user), "principal": principal, "purpose": purpose_name,
			"checked_at": str(checked_at), "result": "allow" if allow else "deny",
		}])
	return {"allow": allow, "status": status, "event": state["event"] if state else None,
	        "principal_ref": principal_ref, "purpose": purpose_name, "checked_at": checked_at}


@frappe.whitelist(methods=["GET"])
def state(principal_ref, programme=None):
	"""Every purpose's current state for one principal (preference centre, host UIs)."""
	frappe.has_permission("Consent State", "read", throw=True)
	principal = _principal(principal_ref)
	rows = enforcement.states_for(principal)
	return [
		{"purpose": p, "status": s["status"], "verification_status": s["verification"], "event": s["event"]}
		for p, s in sorted(rows.items()) if not programme or p.startswith(f"{programme}-")
	]


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
@rate_limit(limit=60, seconds=60)
def verify(hash: str, signature: str | None = None):
	"""Verify a consent artefact without seeing any personal data.

	Returns whether the hash is on this tenant's chain, its position, and whether the signature
	(the one given, or the stored one) verifies with the tenant key."""
	row = frappe.db.get_value(
		"Consent Event", {"hash": hash}, ["chain_seq", "key_id", "signature", "server_time"], as_dict=True
	)
	if not row:
		return {"in_chain": False, "signature_valid": False}
	public_b64 = keystore.public_keys().get(row.key_id)
	sig = signature or row.signature
	return {
		"in_chain": True,
		"chain_seq": row.chain_seq,
		"key_id": row.key_id,
		"recorded_at": row.server_time,
		"signature_valid": bool(public_b64) and signing.verify(public_b64, hash, sig),
	}


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=60, seconds=60)
def public_keys():
	"""This tenant's signing public keys, so anyone can verify an export without us (open-source principle)."""
	return keystore.public_keys()
