# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

from frappe.model.document import Document

from anumati import profile


class Programme(Document):
	def validate(self):
		# Extra questions about the person only once the published notice tells people about them.
		profile.validate_programme(self)
