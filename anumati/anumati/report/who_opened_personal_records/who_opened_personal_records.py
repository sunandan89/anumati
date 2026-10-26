# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE
"""Who opened personal records: the stock View Log (a form was opened) and Access Log (a full name was shown,
a list was searched, evidence was downloaded), for Anumati records only. For the DPO and Admin; Frappe's own
permissions on Access Log and View Log are left as they are (System Manager only)."""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate

WHAT = {"name": _("Saw the full name"), "list": _("Searched the list")}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	start = getdate(filters.from_date or add_days(nowdate(), -30))
	end = add_days(getdate(filters.to_date or nowdate()), 1)
	views = {"reference_doctype": ("like", "Anumati %"), "creation": ("between", [start, end])}
	access = {"export_from": ("like", "Anumati %"), "creation": ("between", [start, end])}
	if filters.user:
		views["viewed_by"] = filters.user
		access["user"] = filters.user
	data = [{"when": r.creation, "who": r.viewed_by, "what": _("Opened the record"),
	         "record_type": r.reference_doctype, "record": r.reference_name}
	        for r in frappe.get_all("View Log", views, ["creation", "viewed_by", "reference_doctype", "reference_name"])]
	data += [{"when": r.creation, "who": r.user, "what": WHAT.get(r.file_type) or _("Opened evidence"),
	          "record_type": r.export_from, "record": r.reference_document}
	         for r in frappe.get_all("Access Log", access, ["creation", "user", "file_type", "export_from", "reference_document"])]
	data.sort(key=lambda r: r["when"], reverse=True)
	columns = [
		{"fieldname": "when", "label": _("When"), "fieldtype": "Datetime", "width": 170},
		{"fieldname": "who", "label": _("Who"), "fieldtype": "Link", "options": "User", "width": 220},
		{"fieldname": "what", "label": _("What"), "fieldtype": "Data", "width": 170},
		{"fieldname": "record_type", "label": _("Record type"), "fieldtype": "Link", "options": "DocType", "width": 200},
		{"fieldname": "record", "label": _("Record"), "fieldtype": "Dynamic Link", "options": "record_type", "width": 200},
	]
	return columns, data
