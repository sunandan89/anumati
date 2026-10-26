import frappe

from anumati.pii import name_index


def execute():
	# Whole-word name search: codes for people saved before the index existed. Names are decrypted in
	# memory only; nothing is logged.
	for name in frappe.get_all("Anumati Data Principal", {"name_index": ("is", "not set")}, pluck="name"):
		doc = frappe.get_doc("Anumati Data Principal", name)
		full_name = doc.get_password("full_name", raise_exception=False)
		if full_name:
			frappe.db.set_value("Anumati Data Principal", name, "name_index", name_index(full_name), update_modified=False)
	# Notice lists show "Village Health Camps v1.0.0" instead of the programme code.
	for row in frappe.get_all("Anumati Notice Template", {"programme_name": ("is", "not set")}, ["name", "programme"]):
		title = frappe.db.get_value("Anumati Programme", row.programme, "programme_name")
		if title:
			frappe.db.set_value("Anumati Notice Template", row.name, "programme_name", title, update_modified=False)
