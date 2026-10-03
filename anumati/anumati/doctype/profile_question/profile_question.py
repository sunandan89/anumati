# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

import re

import frappe
from frappe import _
from frappe.model.document import Document


class ProfileQuestion(Document):
	def before_insert(self):
		# Runs before the record is named from its code.
		self.code = (self.code or "").strip().lower().replace("-", "_").replace(" ", "_")

	def validate(self):
		# The code travels in the field app's sync (principal.upsert profile), whose schema accepts only
		# lower-case letters, digits and underscores.
		if not re.fullmatch(r"[a-z0-9_]{1,64}", self.code):
			frappe.throw(_("Code: use only small letters, numbers and _ (for example ration_card)"))
