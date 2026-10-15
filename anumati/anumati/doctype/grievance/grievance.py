# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, now_datetime

from anumati import grievance, inbox


class Grievance(Document):
	def validate(self):
		# The reply-by clock starts at receipt, not at match.
		if not self.received_on:
			self.received_on = now_datetime()
		if not self.sla_due:
			days = frappe.db.get_single_value("Anumati Settings", "grievance_sla_days") or 30
			self.sla_due = add_days(getdate(self.received_on), days)
		inbox.match(self)
		if self.about_request and self.matched_principal and frappe.db.get_value(
				"Rights Request", self.about_request, "matched_principal") not in (None, self.matched_principal):
			frappe.throw(_("Which request? must be one of this person's requests"))
		if not self.subject:
			self.subject = _(self.category or "something_else")

	def before_insert(self):
		# A complaint about staff goes straight to the DPO, who alone can see it.
		if self.category == grievance.STAFF_ONLY_DPO and not self.dpo_since:
			self.assigned_to = grievance.dpo_user() or self.assigned_to
			self.dpo_since = now_datetime()
