"""Polling feed that mirrors the webhook events (spec gap 6): /api/v2/method/anumati.api.v1.notifications.feed

For hosts that cannot receive webhooks. Carries identifiers and purpose codes only, never personal data."""

import json

import frappe
from frappe import _
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
	out.sort(key=lambda x: x["at"])
	return {"events": out[:limit], "until": out[:limit][-1]["at"] if out else now_datetime()}


@frappe.whitelist(methods=["POST"])
def guardian_needed(programme):
	"""Field app: a worker met an adult who can't decide alone and has no guardian appointed by a court or
	the Local Level Committee, so no consent was taken and nothing about the person was saved. Tells the
	programme's coordinators (Programme Managers) so they can help the family apply. No personal data."""
	frappe.has_permission("Consent Event", "create", throw=True)
	if not frappe.db.exists("Programme", programme):
		frappe.throw(_("Unknown programme {0}").format(programme), frappe.DoesNotExistError)
	name = frappe.db.get_value("Programme", programme, "programme_name")
	worker = frappe.utils.get_fullname(frappe.session.user)
	managers = {u for u in frappe.get_all("Has Role", {"role": "Anumati Programme Manager", "parenttype": "User"},
	                                      pluck="parent") if frappe.db.get_value("User", u, "enabled")}
	allowed = set(frappe.get_all("User Permission", {"allow": "Programme", "for_value": programme}, pluck="user"))
	restricted = set(frappe.get_all("User Permission", {"allow": "Programme"}, pluck="user"))
	# A coordinator restricted to other programmes is not told about this one.
	to = [u for u in managers if u in allowed or u not in restricted]
	for user in to:
		frappe.get_doc({
			"doctype": "Notification Log", "for_user": user, "type": "Alert", "document_type": "Programme",
			"document_name": programme, "from_user": frappe.session.user,
			"subject": _("{0} met an adult who needs a lawful guardian before consent ({1})").format(worker, name),
			"email_content": _("No consent was taken and nothing about the person was saved. The family can apply to "
			                   "the Local Level Committee (National Trust) or a court for a guardian. Ask {0} which "
			                   "family it was.").format(worker),
		}).insert(ignore_permissions=True)
	return {"told": len(to)}
