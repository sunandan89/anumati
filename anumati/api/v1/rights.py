"""Rights API, v1: /api/v2/method/anumati.api.v1.rights.<name>"""

import frappe
from frappe import _

from anumati import rights
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


# ---------------------------------------------------------------- Phase 2a: the other rights (spec B5)
# Staff actions behind the buttons on the Rights Request form. Each checks write permission on the
# request; none returns or logs personal data.


@frappe.whitelist(methods=["POST"])
def send_summary(request):
	"""Access: thread a summary of what is held (never the values) and send it if a template exists."""
	out = rights.send_summary(request)
	return {"request": out["request"], "sent": out["sent"]}


@frappe.whitelist(methods=["POST"])
def mark_corrected(request):
	"""Correction: after editing the principal's record, close with the changed field names."""
	return rights.mark_corrected(request)


@frappe.whitelist(methods=["POST"])
def start_erasure(request, programme=None):
	"""Erasure: withdraw optional purposes and open one Purge Request per purpose held."""
	return rights.start_erasure(request, programme)


@frappe.whitelist(methods=["POST"])
def add_nominee(request, nominee_name, relation, contact=None):
	"""Nomination: store the nominee (encrypted) on the principal and close."""
	return rights.add_nominee(request, nominee_name, relation, contact)


@frappe.whitelist(methods=["POST"])
def close(request, resolution=None, status="Closed"):
	"""Close or reject a request; the principal is told on the channel they used."""
	if status not in ("Closed", "Rejected"):
		frappe.throw(_("status must be Closed or Rejected"))
	doc = rights.close(request, resolution, status)
	return {"request": doc.name, "status": doc.status, "on_time": rights.on_time(doc)}


@frappe.whitelist(methods=["POST"])
def reply(request, template_event="rights_update"):
	"""Reply on the thread with an approved template (SMS needs DLT approval)."""
	return {"communication": rights.reply(request, template_event)}


@frappe.whitelist(methods=["POST"])
def fulfil(request, result, evidence_hash=None):
	"""A host system confirms it carried out a rights request (spec section 8, gap list v0.2.1).
	For erasure this completes the calling system's purge rows for that request."""
	from anumati import channels, propagation

	system = propagation.caller_source_system()
	if result not in ("completed", "failed", "acknowledged"):
		frappe.throw(_("result must be completed, failed or acknowledged"))
	purges = frappe.get_all("Purge Request", {"rights_request": request}, pluck="name")
	acks = frappe.get_all("Propagation Ack", {"source_system": system, "reference_doctype": "Purge Request",
	                                          "reference_name": ("in", purges or ["-"])}, pluck="name")
	for name in acks:
		propagation.record_ack(frappe.get_doc("Propagation Ack", name), result, evidence_hash=evidence_hash)
	if not acks:
		if not frappe.db.exists("Rights Request", request):
			frappe.throw(_("Unknown request"), frappe.DoesNotExistError)
		channels.log(None, "Received", _("{0} reports: {1}").format(system, result), None, channel="api",
		             reference=request, reference_doctype="Rights Request")
	return {"request": request, "system": system, "updated": len(acks)}
