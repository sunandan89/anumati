import frappe

from anumati.ledger import keystore

# The states and actions the Notice Publishing and ROPA Approval workflows use. They are shared, site-wide
# records (an MIS may use "Draft" or "Approve" too), so Anumati adds the missing ones and never changes
# existing ones.
WORKFLOW_STATES = {"Draft": "", "Published": "Success", "Retired": "Inverse", "Approved": "Success"}
WORKFLOW_ACTIONS = ("Publish", "Retire", "Approve", "Send Back")


def after_install():
	# Tenant setup: each site gets its own Ed25519 signing key and phone-hash salt.
	keystore.ensure_keys()
	ensure_workflow_masters()
	# Two-factor sign-in is not switched on here: it is a site-wide setting, so an admin turns it on from
	# Anumati Settings ("Two-factor sign-in for Anumati staff").
	from anumati import profile

	profile.ensure_library()


def after_migrate():
	keystore.ensure_keys()
	ensure_workflow_masters()
	# The library of extra questions a programme can switch on (none are asked by default).
	from anumati import profile

	profile.ensure_library()


def ensure_workflow_masters():
	for state, style in WORKFLOW_STATES.items():
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state, "style": style}).insert(
				ignore_permissions=True
			)
	for action in WORKFLOW_ACTIONS:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(
				ignore_permissions=True
			)


# What uninstalling removes besides Anumati's own DocTypes (which Frappe drops): the records Anumati added
# to stock DocTypes. Workflow states and actions stay, as another app may use them.
UNINSTALL = (
	("Custom Field", {"name": ("like", "%-anumati_%")}),
	("List Filter", {"name": ("like", "anumati-%")}),
	("Kanban Board", {"name": ("in", ["Requests"]), "reference_doctype": ("like", "Anumati %")}),
	("Custom HTML Block", {"name": ("in", ["Needs Attention", "Programmes At A Glance"])}),
	("Notification", {"name": ("like", "Anumati - %")}),
	("Workflow", {"name": ("in", ["Notice Publishing", "ROPA Approval"])}),
)


def before_uninstall():
	for doctype, filters in UNINSTALL:
		for name in frappe.get_all(doctype, filters, pluck="name"):
			frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
