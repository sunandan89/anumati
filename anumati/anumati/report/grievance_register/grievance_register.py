# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE
"""Grievance register: totals by what each grievance was about, for the DPO and audits. Counts only, never
one person's grievance.
Rights requests are not counted here: routine withdrawals are not complaints."""

import statistics

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, getdate, nowdate

from anumati import inbox


def execute(filters=None):
	filters = frappe._dict(filters or {})
	start = getdate(filters.from_date or add_days(nowdate(), -365))
	end = getdate(filters.to_date or nowdate())
	rows = frappe.get_all("Grievance", {"received_on": ("between", [start, add_days(end, 1)])},
	                      ["category", "status", "received_on", "answered_on", "sla_due", "dpo_since", "person_says"])
	today = getdate(nowdate())
	by = {}
	for r in rows:
		b = by.setdefault(r.category, {"received": 0, "answered": 0, "days": [], "dpo": 0, "late": 0, "not_happy": 0})
		b["received"] += 1
		if r.answered_on:
			b["answered"] += 1
			b["days"].append(date_diff(r.answered_on, r.received_on))
		b["dpo"] += 1 if r.dpo_since else 0
		answered_late = r.answered_on and r.sla_due and getdate(r.answered_on) > getdate(r.sla_due)
		still_late = not r.answered_on and r.status not in (inbox.CLOSED,) and r.sla_due and getdate(r.sla_due) < today
		b["late"] += 1 if (answered_late or still_late) else 0
		b["not_happy"] += 1 if r.person_says == "not_happy" else 0
	order = frappe.get_meta("Grievance").get_field("category").options.split("\n")
	data = [{"category": _(c), "received": b["received"], "answered": b["answered"],
	         "typical_days": statistics.median(b["days"]) if b["days"] else None,
	         "dpo": b["dpo"], "late": b["late"], "not_happy": b["not_happy"]}
	        for c in order if (b := by.get(c))]
	columns = [
		{"fieldname": "category", "label": _("What is it about?"), "fieldtype": "Data", "width": 260},
		{"fieldname": "received", "label": _("Received"), "fieldtype": "Int", "width": 100},
		{"fieldname": "answered", "label": _("Answered"), "fieldtype": "Int", "width": 100},
		{"fieldname": "typical_days", "label": _("Typical days to answer"), "fieldtype": "Float", "precision": 1, "width": 170},
		{"fieldname": "dpo", "label": _("Passed to the DPO"), "fieldtype": "Int", "width": 150},
		{"fieldname": "late", "label": _("Late"), "fieldtype": "Int", "width": 90},
		{"fieldname": "not_happy", "label": _("Not happy"), "fieldtype": "Int", "width": 110},
	]
	return columns, data
