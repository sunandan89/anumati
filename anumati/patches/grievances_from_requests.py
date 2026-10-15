"""Complaints were rights requests of type "grievance"; they move to the new Grievance list, with their dates,
person, text and messages. The old request is removed (a note on the grievance keeps its number)."""

import frappe


def execute():
	from anumati import grievance

	frappe.reload_doc("anumati", "doctype", "grievance")
	for name in frappe.get_all("Rights Request", {"request_type": "grievance"}, pluck="name"):
		request = frappe.get_doc("Rights Request", name)
		moved = grievance.move_from_request(request, ignore_permissions=True)
		if request.status in ("request_closed", "cannot_do"):
			frappe.db.set_value("Grievance", moved.name, "status", "request_closed")
		frappe.delete_doc("Rights Request", name, force=True, ignore_permissions=True)
