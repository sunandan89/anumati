"""Enforcement: the Consent State projection and its Redis cache (spec B6, section 9).

Consent Events are the truth; Consent State is a per-purpose projection rebuilt from them, and a Redis
hash per principal serves `consent.check` without touching the database.

Out-of-order sync (spec section 9): an event only moves a purpose's state if it is newer than the event
that last set it, ordered by device_time, then server_time.
"""

import json

import frappe
from frappe.utils import get_datetime, now_datetime

STATUS_FOR_ACTION = {"grant": "granted", "renew": "granted", "withdraw": "withdrawn", "refuse": "refused"}
CACHE_KEY = "anumati:consent:{principal}"


def purpose_name(programme: str, code: str) -> str:
	"""Purpose DocType names are "{programme}-{code}" (autoname)."""
	return f"{programme}-{code}"


def _codes(value) -> list[str]:
	if not value:
		return []
	return json.loads(value) if isinstance(value, str) else list(value)


def _order_key(device_time, server_time):
	device = get_datetime(device_time) if device_time else None
	return (device or get_datetime(server_time), get_datetime(server_time))


def apply_event(event):
	"""Project one sealed Consent Event onto Consent State and refresh the cache."""
	changes = {}
	if event.action in ("grant", "renew"):
		changes.update({code: "granted" for code in _codes(event.purposes_granted)})
		changes.update({code: "refused" for code in _codes(event.purposes_denied)})
	else:
		status = STATUS_FOR_ACTION[event.action]
		changes.update({code: status for code in _codes(event.purposes_granted) + _codes(event.purposes_denied)})

	incoming = _order_key(event.device_time, event.server_time)
	for code, status in changes.items():
		purpose = purpose_name(event.programme, code)
		name = f"{event.principal}-{purpose}"
		if frappe.db.exists("Consent State", name):
			state = frappe.get_doc("Consent State", name, for_update=True)
			last = frappe.db.get_value("Consent Event", state.last_event, ["device_time", "server_time"], as_dict=True)
			if last and _order_key(last.device_time, last.server_time) > incoming:
				continue  # an older event arriving late never overrides a newer decision
		else:
			state = frappe.new_doc("Consent State")
			state.update({"principal": event.principal, "programme": event.programme, "purpose": purpose})
		state.update(
			{"status": status, "verification_status": event.verification_status,
			 "last_event": event.name, "updated": now_datetime()}
		)
		state.flags.ignore_permissions = True
		state.save()
	invalidate(event.principal)


# ------------------------------------------------------------------ cache


def invalidate(principal: str):
	frappe.cache.delete_value(CACHE_KEY.format(principal=principal))


def states_for(principal: str) -> dict[str, dict]:
	"""{purpose_name: {"status", "event"}} for a principal, from Redis, filled from the DB on a miss."""
	key = CACHE_KEY.format(principal=principal)
	cached = frappe.cache.get_value(key)
	if cached is not None:
		return cached
	rows = frappe.get_all(
		"Consent State", {"principal": principal}, ["purpose", "status", "last_event", "verification_status"]
	)
	value = {r.purpose: {"status": r.status, "event": r.last_event, "verification": r.verification_status} for r in rows}
	frappe.cache.set_value(key, value)
	return value


def rebuild(principal: str | None = None):
	"""Rebuild Consent State from the ledger (all principals, or one). Safe to re-run."""
	filters = {"principal": principal} if principal else {}
	frappe.db.delete("Consent State", filters)
	for name in frappe.get_all("Consent Event", filters, pluck="name", order_by="chain_seq asc"):
		apply_event(frappe.get_doc("Consent Event", name))


def set_verification(event_name: str, status: str):
	"""Record a later verification outcome (confirmed / unconfirmed) on the states this event set.
	The event itself never changes (D4); only the projection does."""
	principal = frappe.db.get_value("Consent Event", event_name, "principal")
	for name in frappe.get_all("Consent State", {"last_event": event_name}, pluck="name"):
		frappe.db.set_value("Consent State", name, {"verification_status": status, "updated": now_datetime()})
	if principal:
		invalidate(principal)


def expire_unconfirmed():
	"""Daily: deferred confirmations with no delivery after the programme's window become 'unconfirmed'."""
	from frappe.utils import add_days

	for att in frappe.get_all("Verification Attempt", {"result": "pending", "verification_method": "deferred"},
	                          ["name", "consent_event", "sent_at"]):
		programme = frappe.db.get_value("Consent Event", att.consent_event, "programme")
		days = frappe.db.get_value("Programme", programme, "confirm_window_days") or 7
		if att.sent_at and add_days(att.sent_at, days) < now_datetime():
			frappe.db.set_value("Verification Attempt", att.name, "result", "expired")
			set_verification(att.consent_event, "unconfirmed")
