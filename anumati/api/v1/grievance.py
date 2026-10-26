"""Grievance API, v1: /api/v2/method/anumati.api.v1.grievance.<name>

A grievance is a complaint (DPDP Act s.13). Rights requests (see, correct, delete, nominate, withdraw) stay in
rights.py; the two are kept apart so routine requests never count as complaints."""

import frappe
from frappe import _

from anumati import conversation, grievance, inbox
from anumati.api import schema


@frappe.whitelist(methods=["POST"])
def submit(category, channel, principal_ref=None, description=None, about_request=None, consent_code=None,
           paper_trail_number=None, client_request_id=None):
	"""A grievance from a field worker or a connected system. A retry with the same `client_request_id`
	returns the first grievance (review C10)."""
	frappe.has_permission("Anumati Grievance", "create", throw=True)
	schema.validate("GrievanceSubmit", {k: v for k, v in {
		"category": category, "channel": channel, "principal_ref": principal_ref, "description": description,
		"about_request": about_request, "consent_code": consent_code, "paper_trail_number": paper_trail_number,
		"client_request_id": client_request_id,
	}.items() if v is not None})
	if client_request_id and (seen := frappe.db.get_value(
			"Anumati Grievance", {"client_request_id": client_request_id}, ["name", "status", "sla_due"], as_dict=True)):
		return {"grievance": seen.name, "status": seen.status, "sla_due": seen.sla_due}
	principal = None
	if principal_ref:
		principal = frappe.db.get_value("Anumati Data Principal", {"principal_ref": principal_ref})
		if not principal:
			frappe.throw(_("Unknown principal_ref {0}").format(principal_ref))
	elif consent_code:
		principal = inbox.principal_for_short_code(consent_code)
	doc = grievance.create(category, channel, principal, description=description, about_request=about_request,
	                       raw_payload=description, paper_trail_number=paper_trail_number,
	                       client_request_id=client_request_id, raised_by_role="by_field_worker" if channel in ("field_worker", "slip") else None)
	return {"grievance": doc.name, "status": doc.status, "sla_due": doc.sla_due}


@frappe.whitelist(methods=["POST"])
def reply(grievance, message, kind="update", outcome=None):
	"""Reply to the person (staff): update, question, or the final answer with its outcome
	(put_right, partly_put_right, no_problem_found)."""
	doc = frappe.get_doc("Anumati Grievance", grievance)
	doc.check_permission("write")
	return {"message": conversation.staff_message(doc, message, kind, outcome), "status": doc.status}


@frappe.whitelist(methods=["POST"])
def move_from_request(request):
	"""Staff: a rights request that is really a complaint becomes a grievance; the request is closed."""
	doc = frappe.get_doc("Anumati Rights Request", request)
	frappe.has_permission("Anumati Grievance", "create", throw=True)
	moved = grievance.move_from_request(doc)
	doc.status = inbox.CLOSED
	doc.resolution = ((doc.resolution or "") + " " + _("Moved to grievance {0}.").format(moved.name)).strip()
	doc.save()
	return {"grievance": moved.name}


@frappe.whitelist(methods=["POST"])
def move_to_request(grievance_name, request_type):
	"""Staff: a grievance that is really a rights request moves to the requests inbox; the grievance is closed."""
	doc = frappe.get_doc("Anumati Grievance", grievance_name)
	return {"request": grievance.move_to_request(doc, request_type).name}
