# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

from frappe.model.document import Document

from anumati.pii import is_dummy, sync_hash, sync_name_index


class DataPrincipal(Document):
	def validate(self):
		# full_name and phone are Password fields (encrypted at rest); look people up by phone_hash.
		sync_hash(self, "phone", "phone_hash")
		# Whole-word name search without storing the name: one salted code per word.
		sync_name_index(self)
		if self.phone and not is_dummy(self.phone):
			self.no_phone = 0
