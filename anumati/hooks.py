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
	# Workflow states and actions are shared records: install.ensure_workflow_masters adds missing ones only.
	{"dt": "Workflow", "filters": [["name", "in", ["Notice Publishing", "ROPA Approval"]]]},
	{"dt": "Custom Field", "filters": [["name", "like", "%-anumati_%"]]},
	{"dt": "Notification", "filters": [["name", "like", "Anumati - %"]]},
	# Desk console (tools/gen_desk.py): Needs attention block, Requests board, saved filters.
	{"dt": "Custom HTML Block", "filters": [["name", "in", ["Needs Attention", "Programmes At A Glance"]]]},
	{"dt": "Kanban Board", "filters": [["name", "in", ["Requests"]]]},
	{"dt": "List Filter", "filters": [["name", "like", "anumati-%"]]},
]

after_install = "anumati.install.after_install"
# Removes what Anumati added to stock DocTypes (custom fields, saved filters, board, blocks, workflows).
before_uninstall = "anumati.install.before_uninstall"
after_migrate = ["anumati.install.after_migrate", "anumati.demo.after_migrate", "anumati.evidence.encrypt_existing"]

# Notice audio buttons, loaded only on the two notice forms (not on every Desk page).
doctype_js = {
	"Anumati Notice Template": "public/js/notice_audio.js",
	"Anumati Notice Translation": "public/js/notice_audio.js",
}

# Link fields to a beneficiary also search by whole-word name, full phone number or receipt code.
standard_queries = {"Anumati Data Principal": "anumati.api.v1.principal.link_query"}

# Evidence files (voice, thumbprint, guardian documents) are encrypted on disk right after upload.
doc_events = {"File": {"after_insert": "anumati.evidence.encrypt_file"}}
# Staff-behaviour grievances are for the DPO only; field workers see only the grievances they raised.
# Field workers (and their phones' SDK sync) see only published notices for their own programmes.
permission_query_conditions = {
	"Anumati Grievance": "anumati.grievance.permission_query_conditions",
	"Anumati Notice Template": "anumati.notice_access.notice_conditions",
	"Anumati Notice Translation": "anumati.notice_access.translation_conditions",
}
has_permission = {
	"Anumati Grievance": "anumati.grievance.has_permission",
	"Anumati Notice Template": "anumati.notice_access.notice_permission",
	"Anumati Notice Translation": "anumati.notice_access.translation_permission",
}

scheduler_events = {
	# Seal new Version / Deleted Document records into the signed Audit Entry chain.
	"cron": {"*/10 * * * *": ["anumati.ledger.chain.seal_audit_trail"]},
	"daily": ["anumati.ledger.chain.nightly_verify", "anumati.enforcement.expire_unconfirmed",
	          "anumati.enforcement.flag_new_adults", "anumati.grievance.daily"],
}
