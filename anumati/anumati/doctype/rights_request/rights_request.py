# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate

from anumati import inbox, rights


class RightsRequest(Document):
	def validate(self):
		# SLA clock starts at receipt, not at match (spec section 6).
		if not self.sla_due:
			days = frappe.db.get_single_value("Anumati Settings", "rights_sla_days") or 30
			self.sla_due = add_days(getdate(self.received_on), days)
		inbox.match(self)
		rights.sync_status_fields(self)
