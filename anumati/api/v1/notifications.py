"""Polling feed that mirrors the webhook events (spec gap 6): /api/v2/method/anumati.api.v1.notifications.feed

For hosts that cannot receive webhooks. Carries identifiers and purpose codes only, never personal data."""

import json

import frappe
from frappe.utils import get_datetime, now_datetime

EVENT_FOR_ACTION = {"grant": "consent.recorded", "renew": "consent.recorded", "refuse": "consent.recorded",
                    "withdraw": "consent.withdrawn"}


@frappe.whitelist(methods=["GET"])
def feed(since, limit=100):
	"""Events after `since` (ISO datetime), oldest first. Page by passing the last `at` back as `since`."""
	frappe.has_permission("Consent State", "read", throw=True)
	since, limit = get_datetime(since), min(int(limit or 100), 500)
	events = frappe.get_all(
		"Consent Event", {"server_time": (">", since)},
		["name", "short_code", "action", "principal", "programme", "purposes_granted", "purposes_denied",
		 "verification_status", "server_time"],
		order_by="server_time asc", limit=limit,
	)
	refs = {p.name: p.principal_ref for p in frappe.get_all(
		"Data Principal", {"name": ("in", list({e.principal for e in events}) or ["-"])}, ["name", "principal_ref"])}
	out = [{
		"event": EVENT_FOR_ACTION[e.action], "at": e.server_time, "consent_id": e.name, "short_code": e.short_code,
		"principal_ref": refs.get(e.principal), "programme": e.programme,
		"purposes_granted": json.loads(e.purposes_granted or "[]"), "purposes_denied": json.loads(e.purposes_denied or "[]"),
		"verification_status": e.verification_status,
	} for e in events]
	for r in frappe.get_all("Rights Request", {"modified": (">", since)},
	                        ["name", "request_type", "status", "creation", "modified"], order_by="modified asc", limit=limit):
		out.append({"event": "rights.closed" if r.status in ("Closed", "Rejected") else "rights.created",
		            "at": r.modified, "request": r.name, "request_type": r.request_type, "status": r.status})
	for r in frappe.get_all("Purge Request", {"creation": (">", since), "status": ("!=", "On Hold")},
	                        ["name", "principal", "purpose", "purge_action", "due_on", "creation"], order_by="creation asc", limit=limit):
		out.append({"event": "purge.requested", "at": r.creation, "purge_request": r.name,
		            "principal_ref": frappe.db.get_value("Data Principal", r.principal, "principal_ref"),
		            "purpose": frappe.db.get_value("Purpose", r.purpose, "code"), "action": r.purge_action,
		            "deadline": r.due_on})
	out.sort(key=lambda x: x["at"])
	return {"events": out[:limit], "until": out[:limit][-1]["at"] if out else now_datetime()}
