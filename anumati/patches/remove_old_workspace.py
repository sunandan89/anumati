import frappe


def execute():
	# The single "Anumati" workspace was split into role-based sections (Today, Beneficiaries, ...).
	# Frappe does not delete a standard workspace whose file is gone, so remove the old record.
	if frappe.db.exists("Workspace", "Anumati"):
		frappe.delete_doc("Workspace", "Anumati", force=True, ignore_permissions=True)
