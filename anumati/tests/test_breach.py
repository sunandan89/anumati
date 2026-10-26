"""Breach notification (Breach Incident › Tell affected people): who is told, the message, sending, the field visit
list and results. MSG91 is mocked. Sample data is fictional."""

import uuid
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from anumati import breach, pii
from anumati.anumati.doctype.anumati_breach_incident import anumati_breach_incident as api
from anumati.api.v1 import consent
from anumati.tests.utils import ensure_language, make_principal, make_programme, make_purpose

PROG, DEVICE = "BRN", "BRN-PHONE-1"
TEMPLATES = {
	"en": "{{ org }}: an incident affected your data: {{ what_happened }}. You can: {{ can_do }}. Help: {{ helpline }}. Ref {{ code }}",
	"hi": "{{ org }}: एक घटना हुई: {{ what_happened }}। आप: {{ can_do }}। मदद: {{ helpline }}। कोड {{ code }}",
}


def fake_post(fail=False):
	response = MagicMock(content=b"{}", status_code=200)
	response.json.return_value = {"type": "error"} if fail else {"type": "success", "request_id": f"req-{uuid.uuid4().hex[:8]}"}
	response.raise_for_status.return_value = None
	return patch("anumati.channels.msg91.requests.post", return_value=response)


class TestBreachNotification(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_language("en", "English")
		ensure_language("hi", "Hindi")
		make_programme(PROG, "Breach Test Programme")
		make_purpose(PROG, "screen", "Health screening", essential=1)
		make_purpose(PROG, "photos", "Photos and stories")
		if not frappe.db.exists("Anumati Channel Provider", {"provider_type": "SMS", "enabled": 1}):
			frappe.get_doc({"doctype": "Anumati Channel Provider", "provider_name": "MSG91 breach test", "provider_type": "SMS",
			                "provider": "MSG91", "enabled": 1, "api_key": "test-key"}).insert()
		for lang, body in TEMPLATES.items():
			name = f"breach_notice-sms-{lang}"
			if frappe.db.exists("Anumati Message Template", name):
				frappe.db.set_value("Anumati Message Template", name, {"body": body, "approved": 1, "dlt_template_id": f"flow-breach-{lang}"})
			else:
				frappe.get_doc({"doctype": "Anumati Message Template", "template_event": "breach_notice", "channel": "sms",
				                "language": lang, "body": body, "approved": 1, "dlt_template_id": f"flow-breach-{lang}"}).insert()

	def consent_on_phone(self, person, device=DEVICE, **kw):
		return consent.record({"event_uuid": str(uuid.uuid4()), "principal_ref": person.principal_ref, "programme": PROG,
		                       "purposes_granted": ["screen", "photos"], "channel": "app", "device_id": device,
		                       "device_time": "2026-09-20 11:20:00", **kw})

	def setUp(self):
		self.device = f"{DEVICE}-{uuid.uuid4().hex[:6]}"
		frappe.get_doc({"doctype": "Anumati Field Device", "device_id": self.device, "status": "lost"}).insert()
		self.hindi = make_principal(full_name="Sunita D. (fictional)", phone="5550101001", preferred_language="hi")
		self.english = make_principal(full_name="Asha K. (fictional)", phone="5550101002", preferred_language="en")
		self.nophone = make_principal(full_name="Gauri P. (fictional)", preferred_language="hi", no_phone=1)
		mother = make_principal(full_name="Radha S. (fictional)", phone="5550101003")
		self.child = make_principal(full_name="Meena S. (fictional)", is_minor=1, preferred_language="hi")
		link = frappe.get_doc({"doctype": "Anumati Guardian Link", "principal": self.child.name, "guardian": mother.name,
		                       "guardian_type": "parent", "verification_method": "device_sms_otp"}).insert()
		for p in (self.hindi, self.english, self.nophone):
			self.consent_on_phone(p, self.device)
		self.consent_on_phone(self.child, self.device, guardian_link=link.name, capture_mode="guardian_minor",
		                      purposes_granted=["screen"])
		self.elsewhere = make_principal(phone="5550101009")
		self.consent_on_phone(self.elsewhere, "another-phone")
		self.incident = frappe.get_doc({
			"doctype": "Anumati Breach Incident", "breach_type": "lost_device", "detected_on": frappe.utils.now_datetime(),
			"programme": PROG, "field_device": self.device,
			"what_happened_en": "a field phone was lost", "can_do_en": "ignore calls asking for OTP",
			"what_happened_hi": "एक फ़ील्ड फ़ोन खो गया", "can_do_hi": "OTP माँगने वाले कॉल न सुनें",
		}).insert()

	def test_lost_phone_incident_tells_the_people_whose_data_was_on_it(self):
		self.assertEqual(self.incident.notify_audience, "lost_phone", "set by default for a lost phone")
		names = set(breach.audience(self.incident))
		self.assertEqual(names, {self.hindi.name, self.english.name, self.nophone.name, self.child.name})
		self.assertNotIn(self.elsewhere.name, names)

	def test_counts_route_children_to_the_guardian_and_list_people_without_a_phone(self):
		c = breach.counts(breach.plan(self.incident))
		self.assertEqual((c["total"], c["sms"], c["own"], c["guardian"], c["no_phone"]), (4, 3, 2, 1, 1))
		self.assertEqual(c["languages"], {"hi": 3, "en": 1})

	def test_other_audiences(self):
		self.assertIn(self.elsewhere.name, breach.audience(self.incident, {"notify_audience": "whole_programme"}))
		self.incident.append("purposes_affected", {"purpose": f"{PROG}-photos"})
		self.assertIn(self.hindi.name, breach.audience(self.incident, {"notify_audience": "affected_uses"}))
		ids = f"{self.english.principal_ref}\n  \nNOT-A-REAL-ID\n"
		self.assertEqual(breach.audience(self.incident, {"notify_audience": "id_list", "notify_ids": ids}), [self.english.name])

	def test_summary_has_counts_and_previews_but_no_names_or_numbers(self):
		s = api.summary(self.incident.name)
		self.assertTrue(s["ready"])
		self.assertEqual(s["missing"], [])
		texts = {p["language"]: p["text"] for p in s["previews"]}
		self.assertIn("a field phone was lost", texts["en"])
		self.assertIn("एक फ़ील्ड फ़ोन खो गया", texts["hi"])
		dump = frappe.as_json(s)
		for secret in ("Sunita", "Asha", "5550101001", "5550101003"):
			self.assertNotIn(secret, dump)

	def test_sending_is_off_without_an_approved_template(self):
		frappe.db.set_value("Anumati Message Template", "breach_notice-sms-en", "approved", 0)
		try:
			ready, reason = breach.readiness(self.incident, ["en"])
			self.assertFalse(ready)
			self.assertIn("template", reason)
			self.assertRaises(frappe.ValidationError, api.send, self.incident.name, 3)
		finally:
			frappe.db.set_value("Anumati Message Template", "breach_notice-sms-en", "approved", 1)

	def test_send_needs_the_typed_count_and_happens_once(self):
		self.assertRaises(frappe.ValidationError, api.send, self.incident.name, 2)
		with fake_post() as post:
			out = api.send(self.incident.name, 3)
		self.assertEqual(out, {"queued": 3, "visit": 1})
		self.assertEqual(post.call_count, 3)
		doc = frappe.get_doc("Anumati Breach Incident", self.incident.name)
		self.assertEqual((doc.notify_sent, doc.notify_failed, doc.notifications_sent), (3, 0, 3))
		self.assertTrue(doc.principals_notified_on)
		self.assertEqual(doc.status, "Notifying")
		self.assertEqual([(r.principal_ref, r.reason) for r in doc.visit_list], [(self.nophone.principal_ref, "no_phone")])
		comms = frappe.get_all("Communication", {"reference_doctype": "Anumati Breach Incident", "reference_name": doc.name},
		                       ["content", "phone_no", "anumati_delivery", "anumati_sender_hash"])
		self.assertEqual(len(comms), 3)
		self.assertTrue(all(c.anumati_delivery == "sms_sent" and not c.phone_no for c in comms))
		self.assertTrue(all("555010100" not in c.content for c in comms), "no phone number in the log")
		self.assertIn(pii.phone_hash("5550101003"), {c.anumati_sender_hash for c in comms}, "the child's goes to the guardian")
		self.assertRaises(frappe.ValidationError, api.send, self.incident.name, 3)

	def test_failed_sms_go_on_the_visit_list_and_retry_takes_them_off(self):
		with fake_post(fail=True):
			api.send(self.incident.name, 3)
		doc = frappe.get_doc("Anumati Breach Incident", self.incident.name)
		self.assertEqual(doc.notify_failed, 3)
		self.assertEqual(sorted(r.reason for r in doc.visit_list), ["no_phone", "sms_failed", "sms_failed", "sms_failed"])
		with fake_post():
			out = api.retry(doc.name)
		self.assertEqual(out, {"retried": 3, "sent": 3})
		doc.reload()
		self.assertEqual([r.reason for r in doc.visit_list], ["no_phone"])
		self.assertEqual(breach.results(doc)["failed"], 0, "a retry that got through replaces the failed message")

	def test_results_count_delivery_reports(self):
		with fake_post():
			api.send(self.incident.name, 3)
		comms = frappe.get_all("Communication", {"reference_doctype": "Anumati Breach Incident", "reference_name": self.incident.name},
		                       pluck="name")
		frappe.db.set_value("Communication", comms[0], "anumati_delivery", "sms_delivered")
		frappe.db.set_value("Communication", comms[1], "anumati_delivery", "sms_failed")
		self.assertEqual(breach.results(self.incident), {"sent": 3, "delivered": 1, "failed": 1, "waiting": 1})

	def test_only_the_dpo_can_send(self):
		email = f"breach-admin-{uuid.uuid4().hex[:6]}@example.org"
		user = frappe.get_doc({"doctype": "User", "email": email, "first_name": "Admin (fictional)",
		                       "send_welcome_email": 0, "roles": [{"role": "Anumati Admin"}]}).insert()
		frappe.set_user(user.name)
		try:
			self.assertRaises(frappe.PermissionError, api.send, self.incident.name, 3)
			self.assertFalse(api.summary(self.incident.name)["can_send"])
		finally:
			frappe.set_user("Administrator")

	def test_sms_parts(self):
		self.assertEqual(breach.sms_parts("a" * 160), 1)
		self.assertEqual(breach.sms_parts("a" * 161), 2)
		self.assertEqual(breach.sms_parts("अ" * 70), 1)
		self.assertEqual(breach.sms_parts("अ" * 71), 2)
