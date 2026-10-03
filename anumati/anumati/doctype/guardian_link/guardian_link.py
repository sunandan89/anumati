# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document


class GuardianLink(Document):
	def validate(self):
		# Every guardian except a parent was appointed by an order (court, Local Level Committee or other
		# authority): its number is needed, whether the link comes from Desk, the API or the field app.
		if self.guardian_type != "parent" and not (self.authority_ref or "").strip():
			frappe.throw(_("Enter the order number that appointed this guardian"), frappe.MandatoryError,
			             title=_("Order number needed"))
