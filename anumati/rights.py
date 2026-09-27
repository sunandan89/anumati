"""Rights requests, end to end (spec B5, section 6, T4): access, correction, erasure, grievance, nomination.

Withdrawal fulfilment lives in api/v1/rights.py (Phase 1d). Everything here follows the same rules:
the SLA clock started at receipt; replies go out only through approved Message Templates, in the
principal's language, threaded on the request as Communications; nothing here writes a name, phone
number or other value into a message, log or resolution. Summaries name what is held, never the values."""

import json

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, today

from anumati import channels, enforcement

OPEN = ("Open", "Unmatched", "In Progress", "Awaiting Acknowledgement")
DONE = ("Closed", "Rejected")
PURGE_DONE = ("Completed", "On Hold")

# What the principal record can hold, by field, as the principal would read it.
HELD = (("full_name", "name"), ("phone", "phone number"), ("email", "email"), ("date_of_birth", "date of birth"),
        ("age_band", "age band"), ("preferred_language", "preferred language"),
        ("phone_owner_relation", "whose phone it is"))
ACTION_FOR_POLICY = {"erase": "hard_purge", "anonymise": "anonymise", "ask_processor_to_erase": "hard_purge",
                     "legal_hold_then_review": "legal_hold"}


def _open_request(request, request_type=None):
	doc = frappe.get_doc("Rights Request", request) if isinstance(request, str) else request
	doc.check_permission("write")
	if doc.status in DONE:
		frappe.throw(_("{0} is already {1}").format(doc.name, doc.status))
	if request_type and doc.request_type != request_type:
		frappe.throw(_("{0} is a {1} request").format(doc.name, doc.request_type))
	if not doc.matched_principal:
		frappe.throw(_("Match the request to a principal first"))
	return doc


def _states(principal, programme=None):
	"""Consent State rows for a principal (optionally one programme), with purpose details."""
	filters = {"principal": principal, **({"programme": programme} if programme else {})}
	rows = frappe.get_all("Consent State", filters, ["programme", "purpose", "status", "updated"], order_by="purpose")
	for r in rows:
		r.update(frappe.db.get_value("Purpose", r.purpose, ["code", "purpose_title", "essential", "legal_basis",
		                                                     "retention_policy"], as_dict=True) or {})
	return rows


# ------------------------------------------------------------------ access


def data_summary(principal) -> dict:
	"""What Anumati holds about a principal, without any of the values (spec section 6, Access)."""
	doc = frappe.get_doc("Data Principal", principal)
	states = _states(principal)
	granted = [s.purpose for s in states if s.status == "granted"]
	shared_with = sorted({p.parent for p in frappe.get_all(
		"Processor Purpose", {"parenttype": "Processor", "purpose": ("in", granted or ["-"])}, ["parent"])})
	return {
		"principal_ref": doc.principal_ref,
		"held": [label for field, label in HELD if doc.get(field)],
		"consents": [{"programme": s.programme, "purpose": s.code, "title": s.purpose_title, "status": s.status,
		              "since": str(getdate(s.updated)) if s.updated else None} for s in states],
		"receipts": frappe.get_all("Consent Event", {"principal": principal}, pluck="short_code",
		                           order_by="chain_seq desc", limit=20),
		"shared_with": shared_with,
		"guardians": frappe.db.count("Guardian Link", {"principal": principal}),
		"nominees": len(doc.nominees or []),
	}


def summary_text(summary: dict) -> str:
	lines = [_("What we hold for {0}:").format(summary["principal_ref"]),
	         _("Details: {0}").format(", ".join(summary["held"]) or _("none"))]
	for c in summary["consents"]:
		lines.append(f"- {c['title'] or c['purpose']} ({c['programme']}): {c['status']}")
	if summary["shared_with"]:
		lines.append(_("Shared with: {0}").format(", ".join(summary["shared_with"])))
	if summary["receipts"]:
		lines.append(_("Receipt codes: {0}").format(", ".join(summary["receipts"][:5])))
	return "\n".join(lines)


def send_summary(request) -> dict:
	"""Access right: thread the summary on the request, send it by SMS if an approved template exists,
	and close the request."""
	doc = _open_request(request, "access")
	summary = data_summary(doc.matched_principal)
	text = summary_text(summary)
	channels.log(None, "Sent", text, None, channel="note", reference=doc.name, reference_doctype="Rights Request")
	sent = channels.send(doc.matched_principal, "access_summary", {
		"code": doc.name, "purposes": ", ".join(f"{c['title'] or c['purpose']}: {c['status']}" for c in summary["consents"]),
		"date": today(), "request": doc.name}, channel=doc.channel, reference=doc.name, reference_doctype="Rights Request")
	close(doc, _("Summary of data held prepared{0}.").format(_(" and sent") if sent else ""))
	return {"request": doc.name, "sent": bool(sent), "summary": summary}


# ------------------------------------------------------------------ correction


def changed_fields_since(principal, since) -> list[str]:
	"""Field names changed on the principal since a time, from stock Version records (never the values)."""
	names = set()
	for data in frappe.get_all("Version", {"ref_doctype": "Data Principal", "docname": principal,
	                                       "creation": (">=", since)}, pluck="data"):
		for row in (json.loads(data or "{}").get("changed") or []):
			names.add(row[0])
	return sorted(names)


def mark_corrected(request) -> dict:
	"""Correction right: staff edit the principal's form (values stay encrypted); this records which
	fields changed since the request arrived and closes it."""
	doc = _open_request(request, "correction")
	fields = changed_fields_since(doc.matched_principal, doc.received_on)
	if not fields:
		frappe.throw(_("Nothing has changed on the principal since the request arrived. Edit their record first."))
	close(doc, _("Corrected: {0}.").format(", ".join(fields)))
	return {"request": doc.name, "fields": fields}


# ------------------------------------------------------------------ nomination


def add_nominee(request, nominee_name, relation, contact=None, evidence=None) -> dict:
	"""Nomination right (B5): the nominee is stored encrypted on the principal; SLA is 'on receipt'."""
	doc = _open_request(request, "nomination")
	principal = frappe.get_doc("Data Principal", doc.matched_principal)
	principal.append("nominees", {"nominee_name": nominee_name, "relation": relation, "contact": contact,
	                              "evidence": evidence, "nominated_on": today()})
	principal.save()
	close(doc, _("Nominee recorded ({0}).").format(relation))
	return {"request": doc.name, "nominees": len(principal.nominees)}


# ------------------------------------------------------------------ erasure


def _purge_action(state) -> tuple[str, str | None]:
	"""(purge_action, hold_reason). Purposes kept under a legal obligation go on legal hold for DPO review."""
	if state.legal_basis == "legal_obligation":
		return "legal_hold", _("Kept under a legal obligation; DPO reviews")
	policy_action = frappe.db.get_value("Retention Policy", state.retention_policy, "action_at_expiry") if state.retention_policy else None
	action = ACTION_FOR_POLICY.get(policy_action, "hard_purge")
	return action, (_("Retention policy asks for legal hold then review") if action == "legal_hold" else None)


def start_erasure(request, programme=None) -> dict:
	"""Erasure right: withdraw every optional purpose, then open one Purge Request per purpose held.
	The request waits for every system to acknowledge (Phase 2b) before it can be closed."""
	from anumati.api.v1 import consent

	doc = _open_request(request, "erasure")
	programme = programme or doc.programme
	existing = frappe.get_all("Purge Request", {"rights_request": doc.name}, pluck="name")
	if existing:
		return {"request": doc.name, "purge_requests": existing, "withdrawals": []}

	states = _states(doc.matched_principal, programme)
	if not states:
		frappe.throw(_("No consent is held for this principal{0}.").format(_(" in {0}").format(programme) if programme else ""))
	withdrawals = []
	for prog in sorted({s.programme for s in states}):
		optional = [s.code for s in states if s.programme == prog and s.status == "granted" and not s.essential]
		if optional:
			withdrawals.append(consent.withdraw_for(doc.matched_principal, prog, doc.channel,
			                                        f"er-{frappe.scrub(doc.name)}-{prog}", optional)["short_code"])
	created = []
	for s in states:
		action, reason = _purge_action(s)
		categories = frappe.get_all("Data Category Row", {"parenttype": "Purpose", "parent": s.purpose},
		                            pluck="data_category", limit=1)
		pr = frappe.get_doc({
			"doctype": "Purge Request", "principal": doc.matched_principal, "purpose": s.purpose,
			"data_category": categories[0] if categories else None, "purge_action": action,
			"status": "On Hold" if action == "legal_hold" else "Requested", "due_on": doc.sla_due,
			"rights_request": doc.name, "retention_policy": s.retention_policy,
			"legal_hold": 1 if action == "legal_hold" else 0, "hold_reason": reason,
		})
		pr.insert()
		created.append(pr.name)
	doc.status = "Awaiting Acknowledgement"
	if withdrawals:
		doc.resolution = (doc.resolution or "") + _("Withdrawn first: {0}. ").format(", ".join(withdrawals))
	doc.save()
	return {"request": doc.name, "purge_requests": created, "withdrawals": withdrawals}


def erasure_progress(request) -> dict:
	rows = frappe.get_all("Purge Request", {"rights_request": request}, ["name", "status", "purge_action"])
	return {"total": len(rows), "done": sum(r.status in PURGE_DONE for r in rows),
	        "on_hold": sum(r.status == "On Hold" for r in rows),
	        "pending": [r.name for r in rows if r.status not in PURGE_DONE]}


# ------------------------------------------------------------------ close, reply, overdue


def close(request, resolution=None, status="Closed", notify=True):
	"""Close (or reject) a request and tell the principal, in their language, on the channel they used."""
	doc = frappe.get_doc("Rights Request", request) if isinstance(request, str) else request
	doc.check_permission("write")
	if doc.status in DONE:
		return doc
	if status == "Closed" and doc.request_type == "erasure":
		progress = erasure_progress(doc.name)
		if not progress["total"] or progress["pending"]:
			frappe.throw(_("Erasure is not finished: {0} system confirmation(s) still pending.").format(
				len(progress["pending"])) if progress["total"] else _("Start the erasure first."))
		resolution = resolution or _("Erased; {0} item(s) kept under legal hold.").format(progress["on_hold"])
	if status == "Closed" and doc.request_type == "grievance":
		route = frappe.db.get_single_value("Anumati Settings", "board_complaint_route")
		if route and route not in (resolution or ""):
			resolution = (resolution or "") + " " + _("If you are not satisfied you may complain to the Data Protection Board: {0}").format(route)
	doc.status = status
	if resolution:
		doc.resolution = ((doc.resolution or "") + " " + resolution).strip()
	doc.save()
	if notify and doc.matched_principal:
		frappe.enqueue("anumati.rights.notify_principal", request=doc.name, enqueue_after_commit=True,
		               now=frappe.flags.in_test)
	return doc


def notify_principal(request):
	doc = frappe.get_doc("Rights Request", request)
	return channels.send(doc.matched_principal, "rights_update", {
		"code": doc.name, "request": doc.name, "request_type": doc.request_type, "status": doc.status,
		"date": today(), "board_route": frappe.db.get_single_value("Anumati Settings", "board_complaint_route"),
	}, channel=doc.channel, reference=doc.name, reference_doctype="Rights Request")


def reply(request, template_event="rights_update"):
	"""Staff reply from the thread. Only approved templates go out (DLT); free-text notes stay internal
	as stock Comments, and email replies use the stock email composer on the request."""
	doc = frappe.get_doc("Rights Request", request)
	doc.check_permission("write")
	if not doc.matched_principal:
		frappe.throw(_("Match the request to a principal first"))
	comm = channels.send(doc.matched_principal, template_event, {
		"code": doc.name, "request": doc.name, "request_type": doc.request_type, "status": doc.status,
		"date": today()}, channel=doc.channel, reference=doc.name, reference_doctype="Rights Request")
	if not comm:
		frappe.throw(_("No approved {0} template for this person's language and channel, or no phone on record.").format(template_event))
	return comm


def mark_overdue():
	"""Daily: flag open requests past their SLA date (drives the overdue Notification and analytics)."""
	for name in frappe.get_all("Rights Request", {"status": ("in", OPEN), "sla_due": ("<", today()), "overdue": 0},
	                           pluck="name"):
		doc = frappe.get_doc("Rights Request", name)
		doc.overdue = 1
		doc.flags.ignore_permissions = True
		doc.save()


def on_time(doc) -> bool | None:
	"""Closed on or before its SLA date? None while open."""
	if not doc.closed_on:
		return None
	return getdate(doc.closed_on) <= getdate(doc.sla_due)


def sync_status_fields(doc):
	"""Called from Rights Request.validate: closed_on and overdue follow status."""
	if doc.status in DONE:
		doc.closed_on = doc.closed_on or now_datetime()
		doc.overdue = 0 if getdate(doc.closed_on) <= getdate(doc.sla_due) else doc.overdue
	else:
		doc.closed_on = None
		doc.overdue = 1 if doc.sla_due and getdate(doc.sla_due) < getdate(today()) else 0
