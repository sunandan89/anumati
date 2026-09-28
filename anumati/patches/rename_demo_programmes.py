import frappe


def execute():
	# Demo sites only: give the fictional DEMO programme a realistic name and add the two other fictional
	# demo programmes. Real customer sites have no DEMO programme and are left alone.
	if not frappe.db.exists("Programme", "DEMO"):
		return
	from anumati import demo

	try:
		demo.create_demo_programme()
	except Exception:
		frappe.log_error(title="Anumati: could not update the demo programmes")
