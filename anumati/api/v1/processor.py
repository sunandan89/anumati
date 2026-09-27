"""Partner portal backend (spec C7, section 3a): /api/v2/method/anumati.api.v1.processor.<name>

A processor partner (District Health Office, bank…) sees only the withdrawals and erasures routed to
its own processor record and confirms action taken with proof: an evidence hash or a deletion
reference (spec v0.4). Names are never shown; principals appear by the programme's reference only."""

import frappe
from frappe import _

from anumati import propagation


@frappe.whitelist(methods=["GET"])
def pending():
	processor = propagation.caller_processor()
	rows = frappe.get_all("Propagation Ack", {"processor": processor, "status": ("in", ["Pending", "Sent", "Acknowledged", "Overdue"])},
	                      ["name"], order_by="due_on asc, creation asc", limit=500)
	return {"processor": processor, "requests": [propagation.payload(frappe.get_doc("Propagation Ack", r.name)) for r in rows]}


@frappe.whitelist(methods=["POST"])
def confirm(request_id, evidence_hash=None, deletion_reference=None, status="completed"):
	processor = propagation.caller_processor()
	doc = frappe.get_doc("Propagation Ack", request_id) if frappe.db.exists("Propagation Ack", request_id) else None
	if not doc or doc.processor != processor:
		frappe.throw(_("Unknown request_id"), frappe.DoesNotExistError)
	if str(status).lower() == "completed" and not (evidence_hash or deletion_reference):
		frappe.throw(_("Give an evidence hash or a deletion reference as proof of action"))
	doc = propagation.record_ack(doc, status, evidence_hash=evidence_hash, deletion_reference=deletion_reference)
	return {"request_id": doc.name, "status": doc.status}
