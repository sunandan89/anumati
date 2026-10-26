"""New rights requests and grievances from the field, checked by the records themselves.

Field workers (and connected systems with the same roles) may create Rights Requests and Grievances.
They do it through rights.submit / grievance.submit, or as a plain insert: REST, or the Frappe
Mobile SDK's own sync. A plain insert would otherwise let the sender fill in what only staff decide
(a request already closed, a back-dated receipt, an answer, an outcome), so `prepare` clears those
fields on every new record that does not come from staff or from the server's own code.

The SDK names a record by its phone-made `mobile_uuid`; it becomes the `client_request_id`, so a
retried push is refused by the unique field instead of filing the request twice (review C10)."""

import frappe
from frappe.utils import now_datetime

STAFF_ROLES = {"Anumati Admin", "Anumati DPO", "Anumati Operator", "Anumati Programme Manager", "System Manager"}

# What only staff (or the server) set on a new record. Everything else is what the person or the
# field worker says: the request type or category, the channel, who it is about, their words.
STAFF_ONLY = {
	"Anumati Rights Request": (
		"status", "received_on", "sla_due", "assigned_to", "match_confidence", "candidates", "sender_hash",
		"linked_event", "answer", "answered_on", "resolution", "raised_by",
	),
	"Anumati Grievance": (
		"status", "received_on", "sla_due", "assigned_to", "match_confidence", "candidates", "sender_hash",
		"dpo_since", "outcome", "internal_note", "answer", "answered_on", "person_says", "person_said_on",
		"raised_by",
	),
}


def from_staff_or_server(doc) -> bool:
	"""Server code inserts with ignore_permissions; staff may fill in anything they could later edit."""
	return bool(doc.flags.ignore_permissions) or bool(STAFF_ROLES & set(frappe.get_roles()))


def prepare(doc):
	"""before_insert of Rights Request and Grievance."""
	if not doc.client_request_id and doc.get("mobile_uuid"):
		doc.client_request_id = doc.get("mobile_uuid")
	if from_staff_or_server(doc):
		return
	for field in STAFF_ONLY[doc.doctype]:
		df = doc.meta.get_field(field)
		doc.set(field, df.default if df and df.default and df.fieldtype == "Select" else None)
	# The reply-by clock starts when the server receives it, whatever the sender says.
	doc.received_on = now_datetime()
	if doc.meta.has_field("raised_by_role") and doc.channel in ("field_worker", "slip"):
		doc.raised_by_role = doc.raised_by_role or "by_field_worker"
