app_name = "anumati"
app_title = "Anumati"
app_publisher = "Dhwani RIS"
app_description = "Open-source, field-first DPDP consent platform for nonprofits"
app_email = ""
app_license = "agpl-3.0"
required_apps = ["frappe"]

# Configuration shipped as standard Frappe records (spec: config before code).
fixtures = [
	{"dt": "Role", "filters": [["name", "like", "Anumati %"]]},
	{"dt": "Workflow State", "filters": [["name", "in", ["Draft", "Published", "Retired", "Approved"]]]},
	{"dt": "Workflow Action Master", "filters": [["name", "in", ["Publish", "Retire", "Approve", "Send Back"]]]},
	{"dt": "Workflow", "filters": [["name", "in", ["Notice Publishing", "ROPA Approval"]]]},
	{"dt": "Custom Field", "filters": [["name", "like", "%-anumati_%"]]},
	{"dt": "Notification", "filters": [["name", "like", "Anumati - %"]]},
	# Desk console (tools/gen_desk.py): Needs attention block, Requests board, saved filters,
	# and DPO read access to the stock Access Log / View Log.
	{"dt": "Custom HTML Block", "filters": [["name", "in", ["Needs Attention"]]]},
	{"dt": "Kanban Board", "filters": [["name", "in", ["Requests"]]]},
	{"dt": "List Filter", "filters": [["name", "like", "anumati-%"]]},
	{"dt": "Custom DocPerm", "filters": [["name", "like", "anumati-%"]]},
]

after_install = "anumati.install.after_install"
after_migrate = ["anumati.install.after_migrate", "anumati.demo.after_migrate", "anumati.evidence.encrypt_existing"]

# Link fields to a beneficiary also search by whole-word name, full phone number or receipt code.
standard_queries = {"Data Principal": "anumati.api.v1.principal.link_query"}

# Evidence files (voice, thumbprint, guardian documents) are encrypted on disk right after upload.
doc_events = {"File": {"after_insert": "anumati.evidence.encrypt_file"}}

scheduler_events = {
	# Seal new Version / Deleted Document records into the signed Audit Entry chain.
	"cron": {"*/10 * * * *": ["anumati.ledger.chain.seal_audit_trail"]},
	"daily": ["anumati.ledger.chain.nightly_verify", "anumati.enforcement.expire_unconfirmed"],
}
