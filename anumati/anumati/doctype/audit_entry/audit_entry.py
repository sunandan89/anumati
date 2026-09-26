# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

from frappe.utils import now_datetime

from anumati.ledger.insert_only import InsertOnlyDocument


class AuditEntry(InsertOnlyDocument):
	"""Signed, hash-chained record of an admin action. Holds hashes, never field values."""

	def before_insert(self):
		self.logged_at = self.logged_at or now_datetime()
