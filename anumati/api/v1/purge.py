"""Erasure lifecycle for source systems (spec T15, C6): /api/v2/method/anumati.api.v1.purge.<name>

Field names follow TSI's standardized erasure proposal so a TSI adapter stays thin. The caller must be
the API user of an enabled Source System and only ever sees and acknowledges its own rows."""

import frappe
from frappe import _
from frappe.utils import now_datetime

from anumati import propagation


@frappe.whitelist(methods=["GET"])
def list(limit=None):  # noqa: A001 - the spec names it purge.list
	"""Open purge requests for the calling system, oldest deadline first."""
	system = propagation.caller_source_system()
	cap = frappe.db.get_single_value("Anumati Settings", "purge_batch_limit") or 100
	limit = min(int(limit or cap), cap)
	rows = frappe.get_all("Propagation Ack", {"source_system": system, "reference_doctype": "Purge Request",
	                                          "status": ("in", ["Pending", "Sent", "Overdue"])},
	                      ["name", "status"], order_by="due_on asc, creation asc", limit=limit)
	out = []
	for row in rows:
		ack = frappe.get_doc("Propagation Ack", row.name)
		body = propagation.payload(ack)
		out.append({"request_id": ack.name, "principal_ref": body["principal_ref"], "purposes": body["purposes"],
		            "data_category": body["data_category"], "action": body["action"], "deadline": body["deadline"]})
		if row.status == "Pending":
			frappe.db.set_value("Propagation Ack", ack.name, {"status": "Sent", "sent_at": now_datetime(), "next_retry": None})
	return {"requests": out}


@frappe.whitelist(methods=["POST"])
def ack(request_id, status, evidence_hash=None, completed_at=None):
	"""status = acknowledged | completed | failed. evidence_hash proves what was deleted (SHA-256 hex)."""
	system = propagation.caller_source_system()
	doc = frappe.get_doc("Propagation Ack", request_id) if frappe.db.exists("Propagation Ack", request_id) else None
	if not doc or doc.source_system != system:
		frappe.throw(_("Unknown request_id"), frappe.DoesNotExistError)
	doc = propagation.record_ack(doc, status, evidence_hash=evidence_hash, completed_at=completed_at)
	return {"request_id": doc.name, "status": doc.status}
