# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE
"""Totals of the answers to a programme's extra questions. Never one person's answers: counts under 5 are
shown as "fewer than 5" so a small group can't be singled out."""

import frappe
from frappe import _

SMALL = 5


def execute(filters=None):
	filters = frappe._dict(filters or {})
	conditions = {"parenttype": "Data Principal"}
	if filters.programme:
		conditions["programme"] = filters.programme
	if filters.question:
		conditions["question"] = filters.question
	rows = frappe.get_all("Profile Answer", conditions, ["question", "answer", "count(*) as people"],
	                      group_by="question, answer", order_by="question asc, people desc")
	labels = dict(frappe.get_all("Profile Question", ["name", "question"], as_list=True))
	data = [{"question": labels.get(r.question, r.question), "answer": r.answer,
	         "people": r.people if r.people >= SMALL else _("fewer than {0}").format(SMALL)} for r in rows]
	columns = [
		{"fieldname": "question", "label": _("Question"), "fieldtype": "Data", "width": 240},
		{"fieldname": "answer", "label": _("Answer"), "fieldtype": "Data", "width": 240},
		{"fieldname": "people", "label": _("People"), "fieldtype": "Data", "width": 120},
	]
	return columns, data
