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

from anumati import consent_rules, enforcement
from anumati.consent_rules import ConsentRequestError  # noqa: F401 (re-exported for callers)
from anumati.api import schema
from anumati.ledger import keystore, signing

CAPTURE_FIELDS = (
	"notice", "language", "capture_mode", "channel", "device_id", "device_time", "ip_address", "gps",
	"verification_method", "witness", "evidence", "guardian_link", "source_system",
	"notice_delivery", "notice_completed",
)

# The rules live in the Consent Event DocType (anumati.consent_rules); these names stay for older callers.
_check_purposes = consent_rules.check_purposes
_check_who = consent_rules.check_who


def _parse(value):
	if isinstance(value, str):
		value = json.loads(value)
	return frappe._dict(value or {})


def _principal(principal_ref: str) -> str:
	name = frappe.db.get_value("Anumati Data Principal", {"principal_ref": principal_ref})
	if not name:
		frappe.throw(_("Unknown principal_ref {0}; call principal.upsert first").format(principal_ref), ConsentRequestError)
	return name


def _programme(programme: str):
	if not programme or not frappe.db.exists("Anumati Programme", programme):
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
	"""The code printed on receipts and slips, e.g. AN-7K2Q4C: the first 30 bits of sha256(event_uuid) in
	base32. It depends only on the event_uuid the capture device generates, so an offline field app can
	write the same code on the slip before the event reaches the server. Codes are short and can collide;
	lookups resolve a collision by the sender's phone hash or leave it for a person (inbox)."""
	import base64
	import hashlib

	return "AN-" + base64.b32encode(hashlib.sha256(event_uuid.encode()).digest()[:5]).decode()[:6]


def _existing(event_uuid: str):
	if frappe.db.exists("Anumati Consent Event", event_uuid):
		return _artefact(frappe.get_doc("Anumati Consent Event", event_uuid))
	return None


def _insert(values: dict, ignore_permissions=False) -> dict:
	"""Insert and seal one event. The same event_uuid synced twice at once returns the one that won. Any
	other clash (two writers on the same chain position, which the chain lock should make impossible)
	raises, so the phone keeps the record and retries; it never gets an empty "synced" (review C4)."""
	doc = frappe.get_doc({"doctype": "Anumati Consent Event", **values})
	doc.flags.ignore_permissions = ignore_permissions
	frappe.db.savepoint("anumati_record")
	try:
		doc.insert()
	except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
		frappe.db.rollback(save_point="anumati_record")
		if (existing := _existing(values["event_uuid"])):
			return existing
		raise
	return _artefact(doc)


@frappe.whitelist(methods=["POST"])
def record(event):
	"""Record a grant, refusal or renewal. Returns the signed artefact; replays return the original."""
	event = _parse(event)
	frappe.has_permission("Anumati Consent Event", "create", throw=True)
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
	values = {k: event.get(k) for k in CAPTURE_FIELDS if event.get(k) not in (None, "")}
	# The Consent Event itself checks purposes, who may consent, the notice, evidence and sets the
	# verification status (anumati.consent_rules), so this API and the SDK's sync follow the same rules.
	return _insert(
		{**values, "event_uuid": event.event_uuid, "action": action, "principal": principal, "programme": programme,
		 "purposes_granted": list(event.purposes_granted or []), "purposes_denied": list(event.purposes_denied or []),
		 "verification_status": event.verification_status}
	)


@frappe.whitelist(methods=["POST"])
def withdraw(principal_ref, programme, channel, event_uuid, purposes=None, **extra):
	"""Withdraw consent. Default scope = every optional purpose currently granted (spec section 6)."""
	frappe.has_permission("Anumati Consent Event", "create", throw=True)
	payload = {"principal_ref": principal_ref, "programme": programme, "channel": channel, "event_uuid": event_uuid,
	           **({"purposes": json.loads(purposes) if isinstance(purposes, str) else purposes} if purposes else {}),
	           **{k: v for k, v in extra.items() if k not in ("cmd", "data") and v is not None}}
	schema.validate("ConsentWithdraw", payload)
	paper_trail = extra.pop("paper_trail_number", None)
	leave = frappe.utils.cint(extra.pop("leave_programme", 0))
	principal = _principal(principal_ref)
	artefact = withdraw_for(principal, programme, channel, event_uuid, purposes, leave=leave, **extra)
	if channel in FIELD_CHANNELS:
		_field_request(principal, channel, artefact, paper_trail, leave)
	return artefact


# Withdrawals a field worker carries out on the spot (in person, paper slip or letter).
FIELD_CHANNELS = ("field_worker", "slip")


def _field_request(principal, channel, artefact, paper_trail=None, leave=False):
	"""Keep a closed withdrawal request in the inbox, so every withdrawal, however it arrived, is listed
	there with who logged it and the slip number (spec section 6). Once per event, so a re-sent sync
	does not add a second one."""
	if frappe.db.exists("Anumati Rights Request", {"linked_event": artefact["consent_id"]}):
		return
	doc = frappe.get_doc({
		"doctype": "Anumati Rights Request", "request_type": "withdrawal", "channel": channel, "status": "request_closed",
		"matched_principal": principal, "linked_event": artefact["consent_id"],
		"paper_trail_number": paper_trail or None,
		"resolution": (_("Left the programme. ") if leave else "") + _(
			"Withdrawn in the field by {0}: consent event {1} ({2}).").format(
			frappe.session.user, artefact["consent_id"], artefact["short_code"]),
	})
	doc.flags.ignore_permissions = True
	doc.insert()


def withdraw_for(principal, programme, channel, event_uuid, purposes=None, leave=False, **extra):
	"""Withdrawal without the capture-permission check. Callers must authorise first (the API above, or a
	rights request the operator is allowed to work).

	`leave`: the person leaves the programme. With no `purposes`, every granted purpose is withdrawn,
	essential ones included (S.6(4): any consent can be withdrawn; the programme then stops serving them),
	and once nothing is granted in any programme the person's relationship is marked ended, which starts
	the retention clocks that run from it."""
	if (existing := _existing(event_uuid)):
		return existing
	programme = _programme(programme)
	purposes = json.loads(purposes) if isinstance(purposes, str) else purposes
	if not purposes and leave:
		# Every purpose of the programme, not only those granted now: each gets a withdrawn state at this
		# time, so an older "yes" synced later from another phone cannot turn one back on.
		purposes = frappe.get_all("Anumati Purpose", {"programme": programme}, pluck="code", order_by="code")
	elif not purposes:
		states = enforcement.states_for(principal)
		prefix = f"{programme}-"
		purposes = [
			p[len(prefix):] for p, s in states.items()
			if p.startswith(prefix) and s["status"] == "granted" and not frappe.db.get_value("Anumati Purpose", p, "essential")
		]
	_check_purposes(programme, principal, [], list(purposes))
	values = {k: extra.get(k) for k in CAPTURE_FIELDS if extra.get(k) not in (None, "")}
	values.update(
		{"event_uuid": event_uuid, "action": "withdraw", "principal": principal, "programme": programme,
		 "channel": channel, "purposes_granted": [], "purposes_denied": list(purposes),
		 "verification_status": "recorded", "captured_by": frappe.session.user}
	)
	artefact = _insert(values, ignore_permissions=True)
	if leave:
		_end_relationship_if_done(principal)
	return artefact


def _end_relationship_if_done(principal):
	"""Mark the relationship ended once no purpose is granted in any programme (spec T16)."""
	enforcement.invalidate(principal)
	if any(s["status"] == "granted" for s in enforcement.states_for(principal).values()):
		return
	if not frappe.db.get_value("Anumati Data Principal", principal, "relationship_ended_on"):
		frappe.db.set_value("Anumati Data Principal", principal, "relationship_ended_on", frappe.utils.today())
		frappe.get_doc("Anumati Data Principal", principal).add_comment(
			"Info", _("Left the programme: relationship ended, retention clocks started"))


def _source_system(user: str):
	return frappe.cache.get_value(
		f"anumati:source_system:{user}", generator=lambda: frappe.db.get_value("Anumati Source System", {"api_user": user})
	)


@frappe.whitelist(methods=["GET", "POST"])
def check(principal_ref, purpose, programme=None):
	"""Enforcement gate: may this purpose be processed for this principal right now? Served from cache."""
	frappe.has_permission("Anumati Consent State", "read", throw=True)
	purpose_name = enforcement.purpose_name(programme, purpose) if programme else purpose
	principal = frappe.cache.get_value(
		f"anumati:principal:{principal_ref}",
		generator=lambda: frappe.db.get_value("Anumati Data Principal", {"principal_ref": principal_ref}),
	)
	state = enforcement.states_for(principal).get(purpose_name) if principal else None
	status = state["status"] if state else ("unknown_principal" if not principal else "not_asked")
	allow = status == "granted"
	if allow and frappe.get_cached_value("Anumati Data Principal", principal, "renewal_due"):
		# Turned 18 since a guardian consented: ask the person themselves. Checked first, because a
		# confirmation of the guardian's consent would not help.
		allow, status = False, "renewal_due"
	if allow and state.get("verification") not in ("confirmed", "evidence_only"):
		programme_name = frappe.get_cached_value("Anumati Purpose", purpose_name, "programme")
		minor = frappe.get_cached_value("Anumati Data Principal", principal, "is_minor")
		before_confirm = frappe.get_cached_value("Anumati Programme", programme_name, "allow_processing_before_confirm")
		if minor or not before_confirm:
			allow, status = False, "awaiting_confirmation"
	checked_at = now_datetime()
	if principal:
		from frappe.deferred_insert import deferred_insert

		deferred_insert("Anumati System Usage Log", [{
			"source_system": _source_system(frappe.session.user), "principal": principal, "purpose": purpose_name,
			"checked_at": str(checked_at), "result": "allow" if allow else "deny",
		}])
	return {"allow": allow, "status": status, "event": state["event"] if state else None,
	        "principal_ref": principal_ref, "purpose": purpose_name, "checked_at": checked_at}


@frappe.whitelist(methods=["GET"])
def state(principal_ref, programme=None):
	"""Every purpose's current state for one principal (preference centre, host UIs)."""
	frappe.has_permission("Anumati Consent State", "read", throw=True)
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
		"Anumati Consent Event", {"hash": hash}, ["chain_seq", "key_id", "signature", "server_time"], as_dict=True
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
