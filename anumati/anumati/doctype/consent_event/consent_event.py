# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

import frappe

from anumati import enforcement
from anumati.ledger.canonical import digest_text
from anumati.ledger.insert_only import InsertOnlyDocument
from anumati.pii import is_dummy


class ConsentEvent(InsertOnlyDocument):
	"""Signed, hash-chained consent event. Withdrawal is a new event, never an edit (D4)."""

	def validate(self):
		super().validate()
		# Witness details are encrypted (Password field); only their digest is signed and chained.
		if self.witness and not is_dummy(self.witness):
			self.witness_digest = digest_text(self.witness)

	def after_insert(self):
		# Keep the enforcement projection (Consent State + cache) in step with the ledger.
		enforcement.apply_event(self)
		# Receipts and confirmations go out only after the event is safely committed.
		frappe.enqueue("anumati.channels.on_consent_event", event=self.name, enqueue_after_commit=True)
