"""Beneficiary search with names still encrypted: whole-word name codes, full-number phone hash,
receipt code and ID. The list shows name and masked phone for rows on screen, each view logged.
All sample data is fictional."""

import csv
import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase

from anumati import pii
from anumati.api.v1 import principal
from anumati.tests.test_console import user_with_role
from anumati.tests.utils import make_event, make_principal


class TestBeneficiarySearch(FrappeTestCase):
	def setUp(self):
		self.p = make_principal(full_name="Kavita Yadav", phone="9000011111")

	def test_name_index_holds_codes_not_the_name(self):
		index = frappe.db.get_value("Data Principal", self.p.name, "name_index")
		self.assertTrue(index)
		self.assertNotIn("kavita", index.lower())
		self.assertNotIn("yadav", index.lower())
		self.assertEqual(index, pii.name_index("Kavita Yadav"))

	def test_whole_words_match_in_any_order_and_case(self):
		for q in ("kavita", "KAVITA", "Yadav", "yadav kavita", "Kavita Yadav"):
			self.assertIn(self.p.name, principal.match(q), q)

	def test_partial_or_wrong_words_do_not_match(self):
		for q in ("Kav", "Kavitha", "Kavita Sharma"):
			self.assertNotIn(self.p.name, principal.match(q), q)

	def test_phone_must_be_complete(self):
		for q in ("9000011111", "+91 90000 11111", "09000011111"):
			self.assertIn(self.p.name, principal.match(q), q)
		self.assertNotIn(self.p.name, principal.match("90000"))

	def test_id_and_receipt_code(self):
		self.assertEqual(principal.match(self.p.principal_ref), [self.p.name])
		event = make_event(principal=self.p.name)
		event.reload()
		self.assertIn(self.p.name, principal.match(event.short_code))

	def test_devanagari_names(self):
		p = make_principal(full_name="सीता देवी", phone="9000011112")
		self.assertIn(p.name, principal.match("सीता"))

	def test_renaming_updates_the_index_and_unchanged_saves_keep_it(self):
		doc = frappe.get_doc("Data Principal", self.p.name)
		doc.persona = "patient"
		doc.save()  # the name field holds asterisks now; the index must survive
		self.assertIn(self.p.name, principal.match("kavita"))
		doc.full_name = "Kavita Sharma"
		doc.save()
		self.assertIn(self.p.name, principal.match("sharma"))
		self.assertNotIn(self.p.name, principal.match("yadav"))

	def test_link_field_search_finds_by_name(self):
		rows = principal.link_query("Data Principal", "kavita", "name", 0, 20, {})
		self.assertIn(self.p.name, [r[0] for r in rows])

	def test_search_returns_ids_only(self):
		out = json.dumps(principal.search("kavita"))
		self.assertNotIn("Kavita", out)
		self.assertNotIn("9000011111", out)


class TestListReveal(FrappeTestCase):
	def test_masked_phone_and_one_access_log_per_row(self):
		p = make_principal(full_name="Meena Kumari", phone="9000022222")
		before = frappe.db.count("Access Log", {"reference_document": p.name})
		out = principal.reveal_many(json.dumps([p.name]))
		self.assertEqual(out[p.name], {"full_name": "Meena Kumari", "phone_masked": "9000022XXX"})
		self.assertEqual(frappe.db.count("Access Log", {"reference_document": p.name}), before + 1)

	def test_at_most_100_rows(self):
		self.assertRaises(frappe.ValidationError, principal.reveal_many, json.dumps(["x"] * 101))

	def test_field_workers_cannot_bulk_reveal(self):
		p = make_principal(full_name="Asha Devi", phone="9000033333")
		frappe.set_user(user_with_role("Anumati Field Worker"))
		try:
			self.assertRaises(frappe.PermissionError, principal.reveal_many, json.dumps([p.name]))
		finally:
			frappe.set_user("Administrator")


class TestReadableDesk(FrappeTestCase):
	def test_sms_requests_get_a_subject(self):
		req = frappe.get_doc({"doctype": "Rights Request", "request_type": "withdrawal", "channel": "sms"}).insert()
		self.assertEqual(req.subject, "Withdrawal by SMS")

	def test_links_show_the_beneficiary_id_and_receipt_code(self):
		self.assertTrue(frappe.get_meta("Data Principal").show_title_field_in_link)
		meta = frappe.get_meta("Consent Event")
		self.assertEqual(meta.title_field, "short_code")
		self.assertTrue(meta.show_title_field_in_link)
		self.assertNotIn("event_uuid", [f.fieldname for f in meta.fields if f.in_list_view])

	def test_every_code_and_record_type_has_a_plain_label(self):
		path = os.path.join(frappe.get_app_path("anumati"), "translations", "en.csv")
		with open(path) as fh:
			labels = {row[0]: row[1] for row in csv.reader(fh) if row}
		for doctype in ("Data Principal", "Consent Event", "Consent State", "Rights Request", "ROPA Entry",
		                "Purge Request", "Propagation Ack", "Verification Attempt", "Field Device", "Guardian Link"):
			self.assertIn(doctype, labels, doctype)
		with open(os.path.join(frappe.get_app_path("anumati"), "translations", "hi.csv"), encoding="utf-8") as fh:
			hindi = {row[0] for row in csv.reader(fh) if row}
		self.assertEqual(set(labels) - hindi, set(), "every English label needs a Hindi one (tools/gen_labels.py)")
		for doctype in frappe.get_all("DocType", {"module": "Anumati"}, pluck="name"):
			for f in frappe.get_meta(doctype).fields:
				if f.fieldtype == "Select":
					for option in (f.options or "").split("\n"):
						if "_" in option or option.islower():
							self.assertIn(option, labels, f"{doctype}.{f.fieldname}: {option}")
							self.assertIn(option, hindi, f"{doctype}.{f.fieldname}: {option} (Hindi)")
