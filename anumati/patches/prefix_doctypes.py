"""Every Anumati DocType takes the "Anumati" prefix, so the app installs beside ERPNext and host apps
without name clashes (review A2, A3). Runs before the DocTypes are synced from their new files.

Each DocType is renamed in place with Frappe's own rename, which renames its table and updates the
links, child-table parents and dynamic links that point at it. Data is kept as it is.

Audit Entry rows are sealed into a signed hash chain that includes the DocType name each entry was
about. The rename would rewrite those names and break the chain, so they are put back exactly as they
were sealed: history keeps the name the record had at the time."""

import frappe

OLD_NAMES = (
	"Audit Entry",
	"Audit Share",
	"Audit Share Access",
	"Audit Share Programme",
	"Breach Incident",
	"Breach Purpose",
	"Breach Visit",
	"Campaign",
	"Campaign Channel",
	"Channel Provider",
	"Channel Provider Template",
	"Consent Event",
	"Consent State",
	"Data Category",
	"Data Category Row",
	"Data Principal",
	"Field Device",
	"Funder Link",
	"Grievance",
	"Guardian Link",
	"Language Row",
	"Message Template",
	"Nominee",
	"Notice Processor",
	"Notice Purpose",
	"Notice Purpose Translation",
	"Notice Template",
	"Notice Translation",
	"Processor",
	"Processor Purpose",
	"Profile Answer",
	"Profile Question",
	"Profile Question Label",
	"Programme",
	"Programme Capture Mode",
	"Programme Profile Question",
	"Programme Verification Method",
	"Programme Withdrawal Channel",
	"Propagation Ack",
	"Purge Request",
	"Purpose",
	"ROPA Entry",
	"Retention Policy",
	"Retention System",
	"Rights Request",
	"Source System",
	"System Usage Log",
	"Verification Attempt",
)
PREFIX = "Anumati "


def execute():
	pending = [
		(old, PREFIX + old)
		for old in OLD_NAMES
		if frappe.db.exists("DocType", old) and not frappe.db.exists("DocType", PREFIX + old)
	]
	if not pending:
		return

	sealed = []
	if frappe.db.table_exists("Audit Entry"):
		sealed = frappe.db.sql(
			"select name, ref_doctype from `tabAudit Entry` where ref_doctype in %(names)s",
			{"names": [old for old, _ in pending]},
			as_dict=True,
		)

	for old, new in pending:
		frappe.rename_doc("DocType", old, new, force=True)

	audit_table = "Anumati Audit Entry" if frappe.db.table_exists("Anumati Audit Entry") else "Audit Entry"
	for row in sealed:
		# The table name is one of two fixed names above, never input.
		frappe.db.sql(  # nosemgrep
			f"update `tab{audit_table}` set ref_doctype = %s where name = %s", (row.ref_doctype, row.name)
		)
	frappe.db.commit()
