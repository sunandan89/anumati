# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document

from anumati.ledger import keystore


class AnumatiSettings(Document):
	def validate(self):
		# The spoken yes/no helper sends the person's voice to Sarvam, so Sarvam must be a named Processor
		# (with its agreement) before it can be switched on; notices then list it (Rule 3).
		if self.voice_listen_helper and not frappe.db.exists("Processor", {"processor_name": ("like", "%Sarvam%")}):
			frappe.throw(_("Add Sarvam AI as a Processor, with its data processing agreement, and list it in your notices before switching on the spoken yes/no helper."))

	@frappe.whitelist()
	def rotate_signing_key(self):
		"""New records are signed with a new key; old ones keep verifying with the retired public key.
		The change is recorded by Track Changes and sealed into the audit chain like any other."""
		frappe.only_for("System Manager")
		key_id = keystore.rotate()
		frappe.msgprint(_("Signing key rotated. New key ID: {0}").format(key_id))
		return key_id
