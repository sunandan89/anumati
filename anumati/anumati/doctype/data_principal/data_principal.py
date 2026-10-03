# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

import datetime

from frappe.model.document import Document
from frappe.utils import add_years, getdate, today

from anumati.pii import is_dummy, sync_hash, sync_name_index


class DataPrincipal(Document):
	def validate(self):
		# full_name and phone are Password fields (encrypted at rest); look people up by phone_hash.
		sync_hash(self, "phone", "phone_hash")
		# Whole-word name search without storing the name: one salted code per word.
		sync_name_index(self)
		if self.phone and not is_dummy(self.phone):
			self.no_phone = 0
		self.set_adult_on()

	def set_adult_on(self):
		"""The day a child's own consent is needed. From the date of birth when known; from the year of
		birth, the last day of the year they turn 18 (by then they certainly have)."""
		if self.date_of_birth:
			self.adult_on = add_years(getdate(self.date_of_birth), 18)
		elif self.birth_year:
			self.adult_on = datetime.date(int(self.birth_year) + 18, 12, 31)
		else:
			self.adult_on = None
		if not self.adult_on:
			return
		if getdate(self.adult_on) > getdate(today()):
			self.is_minor = 1
		elif self.is_minor:
			# Turned 18: their guardian's consent stops counting until they consent themselves.
			self.renewal_due = 1
