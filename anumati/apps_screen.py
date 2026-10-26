import frappe

# Roles that open Anumati in Desk. Field workers use the phone app, so they get no tile.
DESK_ROLES = {"Anumati Admin", "Anumati DPO", "Anumati Operator", "Anumati Programme Manager", "System Manager"}


def has_app_permission():
	"""Shows the Anumati tile on the Frappe v16 home screen to staff only."""
	return bool(DESK_ROLES & set(frappe.get_roles()))
