# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

from frappe.model.document import Document


class NoticeTranslation(Document):
	def validate(self):
		# Someone attached their own recording by hand: it is a person's recording, not Sarvam's, so the
		# machine-made flag and any earlier approval no longer apply, and the man's-voice version (made
		# from the old text) is dropped so both voices never say different things.
		if not self.flags.anumati_voice and not self.is_new() and self.has_value_changed("audio_file"):
			self.audio_machine_made = 0
			self.audio_reviewed_by = None
			self.audio_file_male = None
