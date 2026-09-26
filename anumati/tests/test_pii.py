"""PII is encrypted at rest and phone lookups use a salted hash (spec section 9). Sample data is fictional."""

import frappe
from frappe.tests.utils import FrappeTestCase

from anumati import pii
from anumati.tests.utils import make_event, make_principal

NAME, PHONE = "Kamla Devi (fictional)", "+91 90000 12345"


class TestPII(FrappeTestCase):
	def test_name_and_phone_are_not_stored_in_clear(self):
		doc = make_principal(full_name=NAME, phone=PHONE)
		row = frappe.db.sql("select * from `tabData Principal` where name=%s", doc.name, as_dict=True)[0]
		dump = " ".join(str(v) for v in row.values())
		self.assertNotIn("Kamla", dump)
		self.assertNotIn("12345", dump)
		self.assertEqual(doc.get_password("full_name"), NAME)
		self.assertEqual(doc.get_password("phone"), PHONE)

	def test_phone_hash_is_salted_and_normalised(self):
		doc = make_principal(phone=PHONE)
		self.assertEqual(doc.phone_hash, pii.phone_hash("09000012345"))
		self.assertEqual(doc.phone_hash, pii.phone_hash("9000012345"))
		self.assertNotEqual(doc.phone_hash, frappe.utils.sha256_hash("9000012345"))
		self.assertEqual(frappe.db.get_value("Data Principal", {"phone_hash": pii.phone_hash(PHONE)}), doc.name)

	def test_resaving_keeps_the_hash(self):
		doc = make_principal(phone=PHONE)
		before = doc.phone_hash
		doc = frappe.get_doc("Data Principal", doc.name)
		doc.preferred_language = None
		doc.save()
		self.assertEqual(doc.phone_hash, before)

	def test_witness_is_encrypted_and_only_its_digest_is_signed(self):
		event = make_event(witness="Asha worker Sunita (fictional), relation: ASHA")
		stored = frappe.db.get_value("Consent Event", event.name, "witness")
		self.assertNotIn("Sunita", stored or "")
		self.assertEqual(len(event.witness_digest), 64)
