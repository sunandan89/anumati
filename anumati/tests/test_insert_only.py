"""CI gate: Consent Event and Audit Entry are insert-only (saving or deleting an existing one raises)."""

import frappe
from frappe.tests.utils import FrappeTestCase

from anumati.ledger import chain, keystore, signing
from anumati.ledger.insert_only import InsertOnlyError
from anumati.tests.utils import make_event, make_programme

LEDGERS = ("Consent Event", "Audit Entry")


class TestInsertOnly(FrappeTestCase):
	def test_new_event_is_sealed_and_signed(self):
		event = make_event()
		self.assertGreater(event.chain_seq, 0)
		self.assertEqual(len(event.hash), 64)
		self.assertEqual(len(event.prev_hash), 64)
		self.assertTrue(signing.verify(keystore.public_keys()[event.key_id], event.hash, event.signature))

	def test_saving_existing_consent_event_raises(self):
		name = make_event().name
		event = frappe.get_doc("Consent Event", name)
		event.gps = "21.1,79.0"
		self.assertRaises(InsertOnlyError, event.save)

	def test_saving_existing_consent_event_unchanged_raises(self):
		event = frappe.get_doc("Consent Event", make_event().name)
		self.assertRaises(InsertOnlyError, event.save)

	def test_deleting_consent_event_raises(self):
		name = make_event().name
		self.assertRaises(InsertOnlyError, frappe.delete_doc, "Consent Event", name)
		self.assertTrue(frappe.db.exists("Consent Event", name))

	def test_duplicate_event_uuid_is_rejected(self):
		event = make_event()
		self.assertRaises((frappe.DuplicateEntryError, frappe.UniqueValidationError), make_event, event_uuid=event.event_uuid)

	def _audit_entry(self):
		programme = frappe.get_doc("Programme", make_programme())
		programme.programme_name = "Test Health Camp (renamed)"
		programme.save()
		chain.seal_audit_trail()
		name = frappe.db.get_value("Audit Entry", {"ref_doctype": "Programme", "ref_name": programme.name})
		self.assertTrue(name, "editing a Programme should produce a sealed Audit Entry")
		return name

	def test_saving_existing_audit_entry_raises(self):
		entry = frappe.get_doc("Audit Entry", self._audit_entry())
		entry.remarks = "edited"
		self.assertRaises(InsertOnlyError, entry.save)

	def test_deleting_audit_entry_raises(self):
		name = self._audit_entry()
		self.assertRaises(InsertOnlyError, frappe.delete_doc, "Audit Entry", name)

	def test_no_role_may_edit_or_delete_ledgers(self):
		for doctype in LEDGERS:
			meta = frappe.get_meta(doctype)
			self.assertFalse(meta.allow_rename, doctype)
			for perm in meta.permissions:
				for ptype in ("write", "delete", "submit", "cancel", "amend", "import"):
					self.assertFalse(perm.get(ptype), f"{perm.role} has {ptype} on {doctype}")
		for perm in frappe.get_all("Custom DocPerm", {"parent": ("in", LEDGERS)}, ["role", "write", "delete"]):
			self.assertFalse(perm.write or perm.delete, f"Custom permission gives {perm.role} write/delete")

	def test_markup_is_refused_so_stored_equals_signed(self):
		self.assertRaises(frappe.ValidationError, make_event, gps="<b>1</b>")
