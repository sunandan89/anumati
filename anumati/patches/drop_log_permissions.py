import frappe


def execute():
	"""Access Log and View Log go back to Frappe's own permissions (System Manager only). The DPO now reads
	them through the "Who Opened Personal Records" report."""
	frappe.db.delete("Custom DocPerm", {"name": ("like", "anumati-%"), "parent": ("in", ["Access Log", "View Log"])})
	for doctype in ("Access Log", "View Log"):
		frappe.clear_cache(doctype=doctype)
