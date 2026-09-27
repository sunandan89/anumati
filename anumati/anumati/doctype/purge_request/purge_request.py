# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

from frappe.model.document import Document


class PurgeRequest(Document):
	def after_insert(self):
		# Ask every processor and system holding this purpose to act; flag it for a person if none does.
		from anumati import propagation

		propagation.on_purge_request(self)
