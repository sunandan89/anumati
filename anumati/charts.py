"""Breakdown charts for the Analytics section, with readable labels.

Stock Group By charts show stored codes (assisted_thumbprint, DEMO-screen, a user's email). These
charts use the stock Dashboard Chart Source "Anumati Breakdown": the same counts, but each label is a
purpose title, a person's name, a language name or the code's plain label from translations/*.csv
(so Hindi users get Hindi). Counts only; no beneficiary data."""

import frappe
from frappe import _

# chart name -> (DocType, field to group by, filters)
BREAKDOWNS = {
	"Agreed By Purpose": ("Consent State", "purpose", [["status", "=", "granted"]]),
	"How People Consented": ("Consent Event", "capture_mode", [["action", "=", "grant"]]),
	"How The Notice Was Given": ("Consent Event", "notice_delivery", [["action", "!=", "withdraw"]]),
	"Consents By Field Worker": ("Consent Event", "captured_by", [["action", "=", "grant"]]),
	"Consents By Language": ("Consent Event", "language", [["action", "=", "grant"]]),
	"Requests By Type": ("Rights Request", "request_type", []),
	"Verification Pipeline": ("Consent State", "verification_status", [["status", "=", "granted"]]),
	"Withdrawals By Channel": ("Consent Event", "channel", [["action", "=", "withdraw"]]),
}
# Charts that read as a sequence keep this order instead of largest first.
ORDER = {"Verification Pipeline": ["captured", "recorded", "unconfirmed", "confirmed", "evidence_only"]}
LINK_TITLE = {"Purpose": "purpose_title", "Language": "language_name", "User": "full_name"}


def _label(doctype, field, value):
	if not value:
		return _("Not recorded")
	df = frappe.get_meta(doctype).get_field(field)
	if df and df.fieldtype == "Link" and df.options in LINK_TITLE:
		return frappe.db.get_value(df.options, value, LINK_TITLE[df.options]) or value
	return _(value)


@frappe.whitelist()
def breakdown(chart_name=None, chart=None, no_cache=None, filters=None, from_date=None, to_date=None,
			  timespan=None, time_interval=None, heatmap_year=None, refresh=None):
	if chart_name not in BREAKDOWNS:
		frappe.throw(_("Unknown chart"))
	frappe.get_doc("Dashboard Chart", chart_name).check_permission("read")
	doctype, field, base = BREAKDOWNS[chart_name]
	rows = frappe.get_list(doctype, fields=[f"`{field}` as value", "count(*) as count"],
						   filters=base, group_by=f"`tab{doctype}`.`{field}`", order_by="count desc",
						   limit_page_length=20)
	if not rows:
		return None
	if chart_name in ORDER:
		rank = {v: i for i, v in enumerate(ORDER[chart_name])}
		rows.sort(key=lambda r: rank.get(r.value, len(rank)))
	return {"labels": [_label(doctype, field, r.value) for r in rows],
			"datasets": [{"name": _(chart_name), "values": [r.count for r in rows]}]}
