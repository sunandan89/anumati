"""Twilio WhatsApp and voice menus (Phase 2e/2f). Twilio is mocked. Sample data is fictional."""

import uuid
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from anumati import channels, pii
from anumati.api.v1 import consent
from anumati.channels import conversation, twilio
from anumati.tests.utils import ensure_language, make_principal, make_programme, make_purpose

PROG = "TWL"
TOKEN = "twilio-test-auth-token"


def fake_twilio():
	response = MagicMock(content=b"{}", status_code=201)
	response.json.return_value = {"sid": "SM" + uuid.uuid4().hex}
	response.raise_for_status.return_value = None
	return patch("anumati.channels.twilio.requests.post", return_value=response)


class TestTwilio(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_language("en", "English")
		make_programme(PROG, "Twilio Test Programme")
		make_purpose(PROG, "screen", "Health screening", essential=1)
		make_purpose(PROG, "follow", "Follow-up calls")
		make_purpose(PROG, "photos", "Photos and stories")
		if not frappe.db.exists("Channel Provider", "Twilio WhatsApp test"):
			frappe.get_doc({"doctype": "Channel Provider", "provider_name": "Twilio WhatsApp test", "provider_type": "WhatsApp",
			                "provider": "Twilio", "enabled": 1, "api_key": "AC-test", "api_secret": TOKEN,
			                "sender_id": "+14155238886", "webhook_secret": "inbound-test"}).insert()
		if not frappe.db.exists("Message Template", "receipt-sms-en"):
			frappe.get_doc({"doctype": "Message Template", "template_event": "receipt", "channel": "sms", "language": "en",
			                "body": "Consent {{ code }}: {{ purposes }}.", "approved": 1}).insert()

	def setUp(self):
		frappe.cache.delete_keys("anumati:conversation:")

	def person(self, phone, **kw):
		p = make_principal(phone=phone, preferred_language="en", full_name="Lata B. (fictional)", **kw)
		consent.record({"event_uuid": str(uuid.uuid4()), "principal_ref": p.principal_ref, "programme": PROG,
		                "purposes_granted": ["screen", "follow", "photos"], "channel": "app",
		                "device_time": "2026-09-20 11:20:00"})
		return p

	def status(self, p, code):
		return consent.check(p.principal_ref, code, programme=PROG)["status"]

	def test_stop_menu_withdraws_one_purpose(self):
		p = self.person("9000011001")
		h = pii.phone_hash("whatsapp:+919000011001")
		menu = conversation.handle("whatsapp", h, "STOP")
		self.assertIn("Follow-up calls", menu)
		self.assertIn("Photos and stories", menu)
		self.assertNotIn("Health screening", menu)  # essential purposes aren't offered
		self.assertNotIn("Lata", menu)
		options = conversation.get_state(h)["options"]
		n = 2 + [o["code"] for o in options].index("follow")
		reply = conversation.handle("whatsapp", h, str(n))
		self.assertIn("Done", reply)
		self.assertEqual(self.status(p, "follow"), "withdrawn")
		self.assertEqual(self.status(p, "photos"), "granted")
		self.assertEqual(self.status(p, "screen"), "granted")
		req = frappe.get_all("Rights Request", {"matched_principal": p.name, "channel": "whatsapp"}, ["status", "linked_event"])
		self.assertEqual(req[0].status, "Closed")
		self.assertTrue(req[0].linked_event)

	def test_shared_number_asks_who_first_without_names(self):
		a = self.person("9000011002", shared_phone=1)
		b = self.person("9000011002", shared_phone=1)
		h = pii.phone_hash("9000011002")
		who = conversation.handle("whatsapp", h, "stop")
		self.assertIn("more than one person", who)
		self.assertNotIn("Lata", who)
		pick = 1 + [o["principal"] for o in conversation.get_state(h)["options"]].index(b.name)
		conversation.handle("whatsapp", h, str(pick))
		self.assertIn("Done", conversation.handle("whatsapp", h, "1"))
		self.assertEqual((self.status(b, "follow"), self.status(b, "photos")), ("withdrawn", "withdrawn"))
		self.assertEqual(self.status(a, "follow"), "granted")

	def test_erase_and_unknown_numbers_open_requests(self):
		p = self.person("9000011003")
		h = pii.phone_hash("9000011003")
		conversation.handle("whatsapp", h, "STOP")
		self.assertIn("delete", conversation.handle("whatsapp", h, "e"))
		self.assertTrue(frappe.db.exists("Rights Request", {"matched_principal": p.name, "request_type": "erasure", "status": "Open"}))
		reply = conversation.handle("whatsapp", pii.phone_hash("9000011999"), "STOP")
		self.assertIn("could not find", reply)
		self.assertTrue(frappe.db.exists("Rights Request", {"sender_hash": pii.phone_hash("9000011999"), "status": "Unmatched"}))

	def test_voice_menu_press_1_withdraws(self):
		p = self.person("9000011004")
		h = pii.phone_hash("+919000011004")
		spoken, more = conversation.ivr_prompt(h)
		self.assertIn("Press a key", spoken)
		self.assertIn("7. Delete my data", spoken)
		self.assertTrue(more)
		spoken, more = conversation.ivr_prompt(h, "1")
		self.assertIn("Done", spoken)
		self.assertFalse(more)
		self.assertEqual(self.status(p, "follow"), "withdrawn")

	def test_whatsapp_send_uses_twilio_and_falls_back_to_the_sms_wording(self):
		p = self.person("9000011005")
		with fake_twilio() as post:
			comm = channels.send(p.name, "receipt", {"code": "AN-TEST01", "purposes": "Follow-up calls"}, channel="whatsapp")
		self.assertTrue(comm)
		data = post.call_args.kwargs["data"]
		self.assertEqual((data["From"], data["To"]), ("whatsapp:+14155238886", "whatsapp:+919000011005"))
		self.assertIn("AN-TEST01", data["Body"])
		self.assertEqual(frappe.db.get_value("Communication", comm, "anumati_channel"), "whatsapp")
		self.assertFalse(frappe.db.get_value("Communication", comm, "phone_no"))

	def test_webhook_signature_is_checked(self):
		prov = frappe.get_doc("Channel Provider", "Twilio WhatsApp test")
		path = "/api/method/anumati.api.v1.channel.inbound_whatsapp?provider=Twilio+WhatsApp+test&token=inbound-test"
		params = {"From": "whatsapp:+919000011006", "Body": "STOP"}
		site = "https://tenant.example.org"
		good = twilio.signature(TOKEN, site + path, params)
		for sig, ok in ((good, True), ("forged", False), ("", False)):
			frappe.local.request = MagicMock(full_path=path, headers={"X-Twilio-Signature": sig})
			patch("frappe.utils.get_url", return_value=site).start()
			try:
				if ok:
					twilio.check_signature(prov, params)
				else:
					with self.assertRaises(frappe.PermissionError):
						twilio.check_signature(prov, params)
			finally:
				patch.stopall()
				frappe.local.request = None
