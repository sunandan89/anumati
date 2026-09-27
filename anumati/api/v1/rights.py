"""Rights API, v1: /api/v2/method/anumati.api.v1.rights.<name>"""

import frappe
from frappe import _

from anumati.api import schema
from anumati.api.v1 import consent


@frappe.whitelist(methods=["POST"])
def submit(request_type, channel, principal_ref=None, payload=None, paper_trail_number=None):
	"""A rights request from a host system, connector or field worker (spec section 8)."""
	frappe.has_permission("Rights Request", "create", throw=True)
	schema.validate("RightsSubmit", {k: v for k, v in {
		"request_type": request_type, "channel": channel, "principal_ref": principal_ref, "payload": payload,
		"paper_trail_number": paper_trail_number}.items() if v is not None})
	doc = frappe.new_doc("Rights Request")
	doc.update({"request_type": request_type, "channel": channel, "raw_payload": payload,
	            "paper_trail_number": paper_trail_number})
	if principal_ref:
		doc.matched_principal = frappe.db.get_value("Data Principal", {"principal_ref": principal_ref})
		if not doc.matched_principal:
			frappe.throw(_("Unknown principal_ref {0}").format(principal_ref))
	doc.insert()
	return {"request": doc.name, "status": doc.status, "sla_due": doc.sla_due}


@frappe.whitelist(methods=["POST"])
def fulfil_withdrawal(request, programme, purposes=None):
	"""Carry out a withdrawal request: record the signed withdrawal event and close the request.
	Idempotent: the event UUID is derived from the request."""
	doc = frappe.get_doc("Rights Request", request)
	doc.check_permission("write")
	if doc.request_type != "withdrawal":
		frappe.throw(_("Only withdrawal requests can be fulfilled this way"))
	if not doc.matched_principal:
		frappe.throw(_("Match the request to a principal first"))
	artefact = consent.withdraw_for(
		doc.matched_principal, programme, doc.channel, f"rq-{frappe.scrub(doc.name)}-{programme}", purposes
	)
	doc.linked_event = artefact["consent_id"]
	doc.status = "Closed"
	doc.resolution = (doc.resolution or "") + _("Withdrawn by consent event {0} ({1}).").format(
		artefact["consent_id"], artefact["short_code"])
	doc.save()
	return artefact
