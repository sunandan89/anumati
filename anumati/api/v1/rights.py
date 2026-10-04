"""Rights API, v1: /api/v2/method/anumati.api.v1.rights.<name>"""

import frappe
from frappe import _

from anumati import inbox
from anumati.api import schema
from anumati.api.v1 import consent


@frappe.whitelist(methods=["POST"])
def submit(request_type, channel, principal_ref=None, payload=None, paper_trail_number=None, consent_code=None):
	"""A rights request from a host system, connector or field worker (spec section 8). A receipt code
	(`consent_code`, from the person's slip) finds the person when `principal_ref` is not known."""
	frappe.has_permission("Rights Request", "create", throw=True)
	schema.validate("RightsSubmit", {k: v for k, v in {
		"request_type": request_type, "channel": channel, "principal_ref": principal_ref, "payload": payload,
		"paper_trail_number": paper_trail_number, "consent_code": consent_code}.items() if v is not None})
	doc = frappe.new_doc("Rights Request")
	doc.update({"request_type": request_type, "channel": channel, "raw_payload": payload,
	            "paper_trail_number": paper_trail_number})
	if principal_ref:
		doc.matched_principal = frappe.db.get_value("Data Principal", {"principal_ref": principal_ref})
		if not doc.matched_principal:
			frappe.throw(_("Unknown principal_ref {0}").format(principal_ref))
	elif consent_code:
		doc.matched_principal = inbox.principal_for_short_code(consent_code)
	doc.insert()
	return {"request": doc.name, "status": doc.status, "sla_due": doc.sla_due}


@frappe.whitelist(methods=["GET"])
def withdrawable(request):
	"""The uses currently on for the request's person, by programme, for the console's Record withdrawal
	checklist: [{programme, programme_name, code, title, essential}]. Titles and codes only, no personal data."""
	doc = frappe.get_doc("Rights Request", request)
	doc.check_permission("read")
	if not doc.matched_principal:
		return []
	rows = frappe.get_all("Consent State", {"principal": doc.matched_principal, "status": "granted"},
	                      ["programme", "purpose"], order_by="programme, purpose")
	purposes = {p.name: p for p in frappe.get_all(
		"Purpose", {"name": ("in", [r.purpose for r in rows] or ["-"])}, ["name", "code", "purpose_title", "essential"])}
	names = dict(frappe.get_all("Programme", {"name": ("in", list({r.programme for r in rows}) or ["-"])},
	                            ["name", "programme_name"], as_list=True))
	return [
		{"programme": r.programme, "programme_name": names.get(r.programme) or r.programme,
		 "code": purposes[r.purpose].code, "title": purposes[r.purpose].purpose_title,
		 "essential": purposes[r.purpose].essential}
		for r in rows if r.purpose in purposes
	]


@frappe.whitelist(methods=["POST"])
def fulfil_withdrawal(request, programme, purposes=None, leave_programme=0):
	"""Carry out a withdrawal request: record the signed withdrawal event and close the request.
	Idempotent: the event UUID is derived from the request. `leave_programme` withdraws every granted
	purpose, essential ones included (see consent.withdraw_for)."""
	doc = frappe.get_doc("Rights Request", request)
	doc.check_permission("write")
	if doc.request_type != "withdrawal":
		frappe.throw(_("Only withdrawal requests can be fulfilled this way"))
	if not doc.matched_principal:
		frappe.throw(_("Match the request to a principal first"))
	artefact = consent.withdraw_for(
		doc.matched_principal, programme, doc.channel, f"rq-{frappe.scrub(doc.name)}-{programme}", purposes,
		leave=frappe.utils.cint(leave_programme),
	)
	doc.linked_event = artefact["consent_id"]
	doc.status = "Closed"
	doc.resolution = (doc.resolution or "") + _("Withdrawn by consent event {0} ({1}).").format(
		artefact["consent_id"], artefact["short_code"])
	doc.save()
	return artefact
