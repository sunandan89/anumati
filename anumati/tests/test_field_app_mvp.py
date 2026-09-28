"""Field app MVP server features: people for the phone, device check-in and lost phones, translated Rule 3
contents, and how the notice was given (coaching data, never signed). Sample data is fictional."""

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from anumati import demo
from anumati.api.v1 import consent, device, notice, principal
from anumati.ledger import chain


class TestFieldAppMVP(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		demo.create_demo_programme()
		demo.create_field_worker("Mvp@test-2026")

	def grant(self, ref, **kw):
		principal.upsert(ref, full_name="Tara B. (fictional)", phone="5550009999", preferred_language="hi")
		return consent.record({"event_uuid": str(uuid.uuid4()), "principal_ref": ref, "programme": demo.PROGRAMME,
		                       "purposes_granted": ["screen", "follow"], "purposes_denied": ["photos", "research"],
		                       "channel": "app", "device_time": "2026-09-20 11:20:00", **kw})

	def test_people_for_the_phone_include_choices_and_the_receipt_code(self):
		ref = f"MVP-{uuid.uuid4().hex[:6]}"
		art = self.grant(ref)
		out = principal.for_device(demo.PROGRAMME)
		person = next(p for p in out["people"] if p["principal_ref"] == ref)
		self.assertEqual(person["full_name"], "Tara B. (fictional)")
		self.assertEqual(person["last_code"], art["short_code"])
		decisions = {d["purpose"]: d["status"] for d in person["decisions"]}
		self.assertEqual(decisions["follow"], "granted")
		self.assertEqual(decisions["photos"], "refused")
		later = principal.for_device(demo.PROGRAMME, since=out["until"])
		self.assertNotIn(ref, [p["principal_ref"] for p in later["people"]], "paging by since")

	def test_people_for_the_phone_need_permission(self):
		frappe.set_user("Guest")
		try:
			self.assertRaises(frappe.PermissionError, principal.for_device, demo.PROGRAMME)
		finally:
			frappe.set_user("Administrator")

	def test_lost_phone_is_told_to_wipe_once_and_opens_an_incident(self):
		dev = f"DEV-{uuid.uuid4().hex[:6]}"
		self.assertEqual(device.register(dev, app_version="1.0.0", pending=3), {"status": "active", "wipe": False, "voice_helper": False})
		out = device.report_lost(dev)
		self.assertTrue(out["incident"])
		self.assertEqual(frappe.db.get_value("Breach Incident", out["incident"], "principals_affected"), 3)
		self.assertTrue(device.register(dev)["wipe"], "the lost phone is told to wipe itself")
		self.assertEqual(frappe.db.get_value("Field Device", dev, "status"), "wiped")
		self.assertFalse(device.register(dev)["wipe"], "a phone signed in again after the wipe works normally")

	def test_notice_delivery_is_stored_but_not_signed(self):
		ref = f"MVP-{uuid.uuid4().hex[:6]}"
		art = self.grant(ref, notice_delivery="phone_voice", notice_completed=1)
		doc = frappe.get_doc("Consent Event", art["consent_id"])
		self.assertEqual((doc.notice_delivery, doc.notice_completed), ("phone_voice", 1))
		self.assertNotIn("notice_delivery", chain.CONSENT_SCHEMA)
		self.assertEqual(chain.compute_hash(chain.payload(chain.CONSENT_SCHEMA, doc.get), doc.prev_hash), doc.hash)

	def test_hindi_notice_carries_translated_rule3_contents(self):
		out = notice.get_active(demo.PROGRAMME, language="hi")
		self.assertIn("STOP", out["translation"]["withdrawal_methods"])
		self.assertIn("डेटा संरक्षण बोर्ड", out["translation"]["board_complaint_route"])
