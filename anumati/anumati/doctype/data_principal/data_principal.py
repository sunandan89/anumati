# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

from frappe.model.document import Document

from anumati.pii import is_dummy, sync_hash


class DataPrincipal(Document):
	def validate(self):
		# full_name and phone are Password fields (encrypted at rest); look people up by phone_hash.
		sync_hash(self, "phone", "phone_hash")
		if self.phone and not is_dummy(self.phone):
			self.no_phone = 0
