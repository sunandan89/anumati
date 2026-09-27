"""Withdrawal & rights inbox (Phase 1d): SLA clock, shared-number matching, fulfilment, printed receipt.
Sample data is fictional."""

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

from anumati import inbox, pii
from anumati.api.v1 import consent, rights
from anumati.tests.utils import make_principal, make_programme, make_purpose

PROG = "INB"


class TestInbox(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_programme(PROG, "Inbox Test Programme")
		make_purpose(PROG, "screen", "Health screening", essential=1)
		make_purpose(PROG, "follow", "Follow-up calls")

	def grant(self, principal):
		return consent.record({
			"event_uuid": str(uuid.uuid4()), "principal_ref": principal.principal_ref, "programme": PROG,
			"purposes_granted": ["screen", "follow"], "channel": "app", "device_time": "2026-09-20 11:20:00",
		})

	def test_sla_clock_starts_at_receipt(self):
		out = rights.submit("access", "slip", paper_trail_number="PT-0001")
		doc = frappe.get_doc("Rights Request", out["request"])
		days = frappe.db.get_single_value("Anumati Settings", "rights_sla_days") or 30
		self.assertEqual(getdate(doc.sla_due), add_days(getdate(doc.received_on), days))

	def test_single_phone_match_and_shared_phone_left_for_a_person(self):
		one = make_principal(phone="9000033333")
		req = frappe.get_doc({"doctype": "Rights Request", "request_type": "withdrawal", "channel": "sms",
		                      "sender_hash": pii.phone_hash("9000033333")}).insert()
		self.assertEqual(req.matched_principal, one.name)

		a = make_principal(phone="9000044444", shared_phone=1)
		b = make_principal(phone="9000044444", shared_phone=1)
		req = frappe.get_doc({"doctype": "Rights Request", "request_type": "withdrawal", "channel": "sms",
		                      "sender_hash": pii.phone_hash("9000044444")}).insert()
		self.assertEqual(req.status, "Unmatched")
		self.assertFalse(req.matched_principal)
		self.assertIn(a.principal_ref, req.candidates)
		self.assertIn(b.principal_ref, req.candidates)
		self.assertNotIn("9000044444", req.candidates or "")

	def test_fulfilling_a_withdrawal_records_a_signed_event_once(self):
		p = make_principal()
		self.grant(p)
		req = frappe.get_doc({"doctype": "Rights Request", "request_type": "withdrawal", "channel": "slip",
		                      "matched_principal": p.name}).insert()
		first = rights.fulfil_withdrawal(req.name, PROG)
		self.assertEqual(consent.check(p.principal_ref, "follow", programme=PROG)["status"], "withdrawn")
		self.assertEqual(consent.check(p.principal_ref, "screen", programme=PROG)["status"], "granted")
		req.reload()
		self.assertEqual(req.status, "Closed")
		self.assertEqual(req.linked_event, first["consent_id"])
		again = rights.fulfil_withdrawal(req.name, PROG)
		self.assertEqual(again["hash"], first["hash"])

	def test_receipt_code_resolves_to_principal(self):
		p = make_principal()
		art = self.grant(p)
		self.assertTrue(art["short_code"].startswith("AN-"))
		self.assertEqual(inbox.principal_for_short_code(art["short_code"]), p.name)
		self.assertEqual(inbox.principal_for_short_code(art["short_code"][3:].lower()), p.name)

	def test_receipt_code_is_computable_offline_from_the_event_uuid(self):
		# The field app writes the code on the slip before sync; it must equal the server's.
		import base64
		import hashlib

		p = make_principal()
		art = self.grant(p)
		expected = "AN-" + base64.b32encode(hashlib.sha256(art["event_uuid"].encode()).digest()[:5]).decode()[:6]
		self.assertEqual(art["short_code"], expected)
		self.assertEqual(frappe.db.get_value("Consent Event", art["consent_id"], "short_code"), expected)

	def test_colliding_receipt_codes_resolve_by_phone_or_go_to_a_person(self):
		a, b = make_principal(phone="9000055551"), make_principal(phone="9000055552")
		art_a, art_b = self.grant(a), self.grant(b)
		# Force a collision (the ledger is insert-only, so set the column directly in this test).
		frappe.db.set_value("Consent Event", art_b["consent_id"], "short_code", art_a["short_code"], update_modified=False)
		self.assertIsNone(inbox.principal_for_short_code(art_a["short_code"]))
		self.assertEqual(inbox.principal_for_short_code(art_a["short_code"], pii.phone_hash("9000055552")), b.name)
		self.assertIsNone(inbox.principal_for_short_code(art_a["short_code"], pii.phone_hash("9000055559")))

	def test_printed_receipt_shows_code_purposes_and_slip_but_no_name(self):
		p = make_principal(full_name="Radha S. (fictional)")
		art = self.grant(p)
		html = frappe.get_print("Consent Event", art["consent_id"], print_format="Consent Receipt")
		self.assertIn(art["short_code"], html)
		self.assertIn("Follow-up calls", html)
		self.assertIn("Withdrawal slip", html)
		self.assertNotIn("Radha", html)

	def test_sla_notifications_are_installed(self):
		for name in ("Anumati - new rights request", "Anumati - rights request due soon"):
			self.assertTrue(frappe.db.get_value("Notification", name, "enabled"), name)
