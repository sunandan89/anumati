import frappe


def execute():
	"""Install used to switch on two-factor sign-in for the whole site. It is now the Anumati Settings box
	"Two-factor sign-in for Anumati staff"; tick it on sites where it is already on, so nothing changes."""
	if frappe.db.get_single_value("System Settings", "enable_two_factor_auth"):
		frappe.db.set_single_value("Anumati Settings", "staff_two_factor", 1)
