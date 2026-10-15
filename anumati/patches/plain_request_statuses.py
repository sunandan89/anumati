"""Rights requests: the old statuses become the plain words staff and the person both see."""

import frappe

OLD_TO_NEW = {
	"Open": "new_request",
	"Unmatched": "who_is_this",
	"In Progress": "working_on_it",
	"Awaiting Acknowledgement": "waiting_for_partners",
	"Closed": "request_closed",
	"Rejected": "cannot_do",
}


def execute():
	for old, new in OLD_TO_NEW.items():
		frappe.db.sql("update `tabRights Request` set status=%s where status=%s", (new, old))
	# The old Requests board columns are rebuilt from the fixture.
	if frappe.db.exists("Kanban Board", "Requests"):
		frappe.delete_doc("Kanban Board", "Requests", force=True, ignore_permissions=True)
	# The "Unmatched" saved filter is now "Who is this" (its fixture comes back under the new name).
	if frappe.db.exists("List Filter", "anumati-rights_request-unmatched"):
		frappe.delete_doc("List Filter", "anumati-rights_request-unmatched", force=True, ignore_permissions=True)
