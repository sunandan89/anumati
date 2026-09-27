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
]

after_install = "anumati.install.after_install"
after_migrate = "anumati.install.after_migrate"

scheduler_events = {
	# Seal new Version / Deleted Document records into the signed Audit Entry chain.
	"cron": {"*/10 * * * *": ["anumati.ledger.chain.seal_audit_trail"]},
	"daily": ["anumati.ledger.chain.nightly_verify", "anumati.enforcement.expire_unconfirmed",
	          "anumati.rights.mark_overdue"],
}
