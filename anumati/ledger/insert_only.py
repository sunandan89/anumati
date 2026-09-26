"""Shared controller for the insert-only ledgers (Consent Event, Audit Entry).

Uses only documented controller hooks:
  validate    - refuses any save of an existing record
  before_save - seals a new record into the chain (position, hash, signature)
  on_trash    - refuses deletion
Permissions grant no write or delete to any role, and allow_rename is off. A change made directly in
the database bypasses all of this; the hash chain and the nightly verifier detect it.
"""

import frappe
from frappe.model.document import Document

from anumati.ledger import chain


class InsertOnlyError(frappe.PermissionError):
	pass


class InsertOnlyDocument(Document):
	def validate(self):
		if not self.is_new():
			raise InsertOnlyError(f"{self.doctype} is insert-only: an existing record cannot be changed")
		chain.check_sealable(self)

	def before_save(self):
		if self.is_new():
			chain.seal(self)

	def on_trash(self):
		raise InsertOnlyError(f"{self.doctype} is insert-only: records cannot be deleted")
