"""SMS channel (Phase 1c) with MSG91 mocked: receipts, server OTP, deferred confirmation, inbound keywords,
missed calls, delivery reports. No real message is sent. Sample data is fictional."""

import json
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from anumati import channels, enforcement, pii
from anumati.api.v1 import channel, consent, verification
from anumati.tests.utils import ensure_language, make_principal, make_programme, make_purpose

PROG, SECRET = "SMS", "test-inbound-secret"
TEMPLATES = {
	"receipt": "Consent {{ code }} for {{ programme }}: {{ purposes }}. Reply STOP to withdraw.",
	"withdrawal_confirmation": "Withdrawn: {{ purposes }} ({{ code }}).",
	"otp": "Your code is {{ otp }}.",
	"deferred_confirmation": "You consented on {{ date }} to {{ purposes }}. Reply STOP to withdraw.",
}


def fake_post():
	response = MagicMock(content=b"{}", status_code=200)
	response.json.return_value = {"type": "success", "request_id": f"req-{uuid.uuid4().hex[:8]}"}
	response.raise_for_status.return_value = None
	return patch("anumati.channels.msg91.requests.post", return_value=response)


class TestChannels(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_language("en", "English")
		make_programme(PROG, "SMS Test Programme")
		make_purpose(PROG, "screen", "Health screening", essential=1)
		make_purpose(PROG, "follow", "Follow-up calls")
		make_purpose(PROG, "photos", "Photos and stories")
		if not frappe.db.exists("Channel Provider", "MSG91 test"):
			frappe.get_doc({"doctype": "Channel Provider", "provider_name": "MSG91 test", "provider_type": "SMS",
			                "provider": "MSG91", "enabled": 1, "api_key": "test-key", "webhook_secret": SECRET}).insert()
		for event, body in TEMPLATES.items():
			if not frappe.db.exists("Message Template", f"{event}-sms-en"):
				frappe.get_doc({"doctype": "Message Template", "template_event": event, "channel": "sms", "language": "en",
				                "body": body, "approved": 1, "dlt_template_id": f"flow-{event}"}).insert()

	def grant(self, principal, **kw):
		return consent.record({"event_uuid": str(uuid.uuid4()), "principal_ref": principal.principal_ref,
		                       "programme": PROG, "purposes_granted": ["screen", "follow", "photos"],
		                       "channel": "app", "device_time": "2026-09-20 11:20:00", **kw})

	def person(self, phone):
		return make_principal(phone=phone, preferred_language="en")

	def test_receipt_is_sent_and_logged_without_the_number(self):
		p = self.person("9000077001")
		art = self.grant(p)
		with fake_post() as post:
			channels.on_consent_event(art["consent_id"])
		payload = post.call_args.kwargs["json"]
		self.assertEqual(payload["template_id"], "flow-receipt")
		self.assertEqual(payload["recipients"][0]["mobiles"], "919000077001")
		self.assertEqual(payload["recipients"][0]["code"], art["short_code"])
		comm = frappe.get_doc("Communication", {"anumati_consent_event": art["consent_id"]})
		self.assertFalse(comm.phone_no)
		self.assertEqual(comm.anumati_sender_hash, pii.phone_hash("9000077001"))
		self.assertNotIn("9000077001", comm.content)

	def test_no_provider_means_no_send_and_no_error(self):
		p = self.person("9000077002")
		art = self.grant(p)
		frappe.db.set_value("Channel Provider", "MSG91 test", "enabled", 0)
		try:
			with fake_post() as post:
				channels.on_consent_event(art["consent_id"])
			post.assert_not_called()
		finally:
			frappe.db.set_value("Channel Provider", "MSG91 test", "enabled", 1)

	def test_server_otp_confirms_consent(self):
		p = self.person("9000077003")
		art = self.grant(p)
		with fake_post() as post:
			out = verification.send_otp(art["consent_id"])
		self.assertTrue(out["sent"])
		code = post.call_args.kwargs["json"]["recipients"][0]["otp"]
		self.assertFalse(verification.verify_otp(art["consent_id"], "000000" if code != "000000" else "111111")["confirmed"])
		self.assertTrue(verification.verify_otp(art["consent_id"], code)["confirmed"])
		states = consent.state(p.principal_ref, programme=PROG)
		self.assertTrue(all(s["verification_status"] == "confirmed" for s in states))

	def test_deferred_confirmation_confirmed_by_delivery_or_expires(self):
		p = self.person("9000077004")
		art = self.grant(p, verification_method="deferred")
		with fake_post() as post:
			channels.on_consent_event(art["consent_id"])
		request_id = post.return_value.json.return_value["request_id"]
		channel.delivery_report(provider="MSG91 test", token=SECRET, request_id=request_id, status="delivered")
		self.assertTrue(consent.check(p.principal_ref, "follow", programme=PROG)["allow"])
		self.assertEqual(consent.state(p.principal_ref, programme=PROG)[0]["verification_status"], "confirmed")

		q = self.person("9000077005")
		art2 = self.grant(q, verification_method="deferred")
		with fake_post():
			channels.on_consent_event(art2["consent_id"])
		att = frappe.db.get_value("Verification Attempt", {"consent_event": art2["consent_id"]})
		frappe.db.set_value("Verification Attempt", att, "sent_at", now_datetime() - timedelta(days=30))
		enforcement.expire_unconfirmed()
		self.assertEqual(frappe.db.get_value("Verification Attempt", att, "result"), "expired")
		self.assertEqual(consent.state(q.principal_ref, programme=PROG)[0]["verification_status"], "unconfirmed")

	def test_inbound_stop_withdraws_optional_purposes(self):
		p = self.person("9000077006")
		self.grant(p)
		out = channel.inbound_sms(provider="MSG91 test", token=SECRET, sender="+91 90000 77006", message="stop")
		self.assertEqual(out["outcome"], "withdrawn")
		self.assertEqual(consent.check(p.principal_ref, "follow", programme=PROG)["status"], "withdrawn")
		self.assertEqual(consent.check(p.principal_ref, "screen", programme=PROG)["status"], "granted")
		self.assertEqual(frappe.db.get_value("Rights Request", out["request"], "status"), "Closed")

	def test_inbound_stop_n_and_stop_code_with_devanagari_digits(self):
		p = self.person("9000077007")
		art = self.grant(p)
		out = channel.inbound_sms(provider="MSG91 test", token=SECRET, sender="9000077007", message="STOP ३")
		self.assertEqual(out["outcome"], "withdrawn")
		self.assertEqual(consent.check(p.principal_ref, "photos", programme=PROG)["status"], "withdrawn")
		self.assertEqual(consent.check(p.principal_ref, "follow", programme=PROG)["status"], "granted")

		shared_a, shared_b = self.person("9000077008"), self.person("9000077008")
		art_b = self.grant(shared_b)
		out = channel.inbound_sms(provider="MSG91 test", token=SECRET, sender="9000077008", message=f"STOP {art_b['short_code']}")
		self.assertEqual(out["outcome"], "withdrawn")
		self.assertEqual(consent.check(shared_b.principal_ref, "follow", programme=PROG)["status"], "withdrawn")
		self.assertIsNotNone(art)

	def test_shared_number_without_code_goes_to_a_person(self):
		self.person("9000077009"), self.person("9000077009")
		out = channel.inbound_sms(provider="MSG91 test", token=SECRET, sender="9000077009", message="STOP")
		self.assertEqual(out["outcome"], "unmatched")
		self.assertEqual(frappe.db.get_value("Rights Request", out["request"], "status"), "Unmatched")

	def test_data_help_and_missed_call_open_requests(self):
		p = self.person("9000077010")
		data = channel.inbound_sms(provider="MSG91 test", token=SECRET, sender="9000077010", message="DATA")
		self.assertEqual(frappe.db.get_value("Rights Request", data["request"], "request_type"), "access")
		missed = channel.missed_call(provider="MSG91 test", token=SECRET, caller="9000077010")
		req = frappe.get_doc("Rights Request", missed["request"])
		self.assertEqual((req.request_type, req.channel, req.matched_principal), ("withdrawal", "missed_call", p.name))
		self.assertNotEqual(req.status, "Closed", "a missed call is confirmed by a person, never auto-applied")

	def test_callbacks_reject_a_wrong_secret(self):
		for fn, kw in ((channel.inbound_sms, {"sender": "9000077011", "message": "STOP"}),
		               (channel.missed_call, {"caller": "9000077011"}),
		               (channel.delivery_report, {"request_id": "x", "status": "delivered"})):
			self.assertRaises(frappe.PermissionError, fn, provider="MSG91 test", token="wrong", **kw)
			self.assertRaises(frappe.PermissionError, fn, provider="MSG91 test", token=None, **kw)

	def test_message_bodies_never_contain_names(self):
		p = make_principal(full_name="Gauri P. (fictional)", phone="9000077012", preferred_language="en")
		art = self.grant(p)
		with fake_post():
			channels.on_consent_event(art["consent_id"])
		content = frappe.db.get_value("Communication", {"anumati_consent_event": art["consent_id"]}, "content")
		self.assertNotIn("Gauri", content)
		self.assertEqual(json.loads(json.dumps(content)), content)

	# -- server-sent codes (the worker never sees the code) -----------------------

	def test_code_never_appears_in_the_message_log(self):
		p = self.person("9000077101")
		art = self.grant(p)
		with fake_post() as post:
			verification.send_otp(art["consent_id"])
		code = post.call_args.kwargs["json"]["recipients"][0]["otp"]
		comm = frappe.get_last_doc("Communication", {"anumati_consent_event": art["consent_id"]})
		self.assertNotIn(code, comm.content)

	def test_dhwani_sendotp_template_passes_anumatis_own_code(self):
		p = self.person("9000077102")
		art = self.grant(p)
		frappe.db.set_value("Message Template", "otp-sms-en", {"send_via": "SendOTP", "dlt_template_id": "otp-tmpl"})
		try:
			with fake_post() as post:
				out = verification.send_otp(art["consent_id"])
			self.assertTrue(out["sent"])
			self.assertEqual(out["to"], "9000077XXX")
			self.assertTrue(post.call_args.args[0].endswith("/api/v5/otp"))
			params = post.call_args.kwargs["params"]
			self.assertEqual((params["template_id"], params["mobile"]), ("otp-tmpl", "919000077102"))
			self.assertTrue(verification.verify_otp(art["consent_id"], params["otp"])["confirmed"])
		finally:
			frappe.db.set_value("Message Template", "otp-sms-en", {"send_via": "Flow", "dlt_template_id": "flow-otp"})

	def test_codes_are_limited_and_not_sent_without_setup(self):
		p = self.person("9000077103")
		art = self.grant(p)
		with fake_post():
			for _ in range(verification.MAX_SENDS):
				verification.send_otp(art["consent_id"])
			self.assertRaises(frappe.ValidationError, verification.send_otp, art["consent_id"])
		q = self.person("9000077104")
		art2 = self.grant(q)
		frappe.db.set_value("Channel Provider", "MSG91 test", "enabled", 0)
		try:
			self.assertEqual(verification.send_otp(art2["consent_id"]), {"sent": False, "reason": "not_set_up"})
		finally:
			frappe.db.set_value("Channel Provider", "MSG91 test", "enabled", 1)

	def test_only_the_capturing_worker_or_staff_can_verify(self):
		from anumati.tests.test_console import user_with_role

		art = self.grant(self.person("9000077105"))
		frappe.set_user(user_with_role("Anumati Field Worker"))
		try:
			self.assertRaises(frappe.PermissionError, verification.send_otp, art["consent_id"])
		finally:
			frappe.set_user("Administrator")

	def test_a_phone_cannot_claim_a_code_confirmed(self):
		for method in ("device_sms_otp", "server_otp"):
			p = self.person("90000772" + ("01" if method == "device_sms_otp" else "02"))
			self.grant(p, verification_method=method, verification_status="confirmed",
			           evidence=[{"file": "/private/files/haan-sample.m4a", "kind": "audio"}])
			self.assertEqual(consent.state(p.principal_ref, programme=PROG)[0]["verification_status"], "recorded", method)
