"""Rights requests end to end (Phase 2a, spec B5): access, correction, erasure, grievance, nomination,
overdue flag, replies only with approved templates, threaded messages. SMS is mocked. Sample data is
fictional."""

import json
import uuid

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from anumati import rights as rights_core
from anumati.api.v1 import channel, consent, rights
from anumati.tests.test_channels import SECRET, fake_post
from anumati.tests.utils import ensure_language, make_principal, make_programme, make_purpose

PROG = "RGT"
PHONE = "9000088001"


class TestRights(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_language("en", "English")
		make_programme(PROG, "Rights Test Programme")
		make_purpose(PROG, "screen", "Health screening", essential=1)
		make_purpose(PROG, "follow", "Follow-up calls")
		make_purpose(PROG, "ledger", "Disbursement ledger", essential=1, legal_basis="legal_obligation")
		if not frappe.db.exists("Channel Provider", "MSG91 test"):
			frappe.get_doc({"doctype": "Channel Provider", "provider_name": "MSG91 test", "provider_type": "SMS",
			                "provider": "MSG91", "enabled": 1, "api_key": "test-key", "webhook_secret": SECRET}).insert()
		for event, body in {"rights_update": "Request {{ code }} is {{ status }}.",
		                    "access_summary": "We hold for you: {{ purposes }} ({{ code }})."}.items():
			if not frappe.db.exists("Message Template", f"{event}-sms-en"):
				frappe.get_doc({"doctype": "Message Template", "template_event": event, "channel": "sms", "language": "en",
				                "body": body, "approved": 1, "dlt_template_id": f"flow-{event}"}).insert()

	def person(self, **kw):
		p = make_principal(preferred_language="en", **kw)
		consent.record({"event_uuid": str(uuid.uuid4()), "principal_ref": p.principal_ref, "programme": PROG,
		                "purposes_granted": ["screen", "follow", "ledger"], "channel": "app",
		                "device_time": "2026-09-20 11:20:00"})
		return p

	def request(self, request_type, principal, channel="slip", **kw):
		return frappe.get_doc({"doctype": "Rights Request", "request_type": request_type, "channel": channel,
		                       "matched_principal": principal.name, **kw}).insert()

	def thread(self, request):
		return frappe.get_all("Communication", {"reference_doctype": "Rights Request", "reference_name": request},
		                      ["content", "anumati_channel", "sent_or_received"])

	# ------------------------------------------------------------ access

	def test_access_summary_names_what_is_held_never_the_values(self):
		p = self.person(full_name="Meera K. (fictional)", phone=PHONE)
		req = self.request("access", p, channel="sms")
		with fake_post():
			out = rights.send_summary(req.name)
		self.assertTrue(out["sent"])
		summary = rights_core.data_summary(p.name)
		self.assertIn("name", summary["held"])
		self.assertIn("phone number", summary["held"])
		self.assertEqual({c["purpose"]: c["status"] for c in summary["consents"]},
		                 {"screen": "granted", "follow": "granted", "ledger": "granted"})
		blob = json.dumps(summary) + json.dumps(self.thread(req.name))
		self.assertNotIn("Meera", blob)
		self.assertNotIn(PHONE, blob)
		self.assertEqual(frappe.db.get_value("Rights Request", req.name, "status"), "Closed")

	# ------------------------------------------------------------ correction

	def test_correction_closes_with_field_names_only(self):
		p = self.person(full_name="Old Name (fictional)")
		req = self.request("correction", p)
		with self.assertRaises(frappe.ValidationError):
			rights.mark_corrected(req.name)  # nothing edited yet
		doc = frappe.get_doc("Data Principal", p.name)
		doc.email = "meera.fictional@example.org"
		doc.save(ignore_version=False)  # Frappe skips Version in tests by default
		out = rights.mark_corrected(req.name)
		self.assertIn("email", out["fields"])
		resolution = frappe.db.get_value("Rights Request", req.name, "resolution")
		self.assertIn("email", resolution)
		self.assertNotIn("example.org", resolution)

	# ------------------------------------------------------------ erasure

	def test_erasure_withdraws_then_waits_for_every_purge_before_closing(self):
		p = self.person()
		req = self.request("erasure", p, channel="field_worker")
		out = rights.start_erasure(req.name)
		self.assertEqual(consent.check(p.principal_ref, "follow", programme=PROG)["status"], "withdrawn")
		self.assertEqual(len(out["purge_requests"]), 3)
		purges = {frappe.db.get_value("Purge Request", n, "purpose"): frappe.get_doc("Purge Request", n)
		          for n in out["purge_requests"]}
		held = purges[f"{PROG}-ledger"]
		self.assertEqual((held.purge_action, held.status, held.legal_hold), ("legal_hold", "On Hold", 1))
		self.assertEqual(frappe.db.get_value("Rights Request", req.name, "status"), "Awaiting Acknowledgement")
		# idempotent
		self.assertEqual(sorted(rights.start_erasure(req.name)["purge_requests"]), sorted(out["purge_requests"]))

		with self.assertRaises(frappe.ValidationError):
			rights.close(req.name)  # systems haven't confirmed yet
		for pr in purges.values():
			if pr.status != "On Hold":
				pr.status = "Completed"
				pr.save()
		closed = rights.close(req.name)
		self.assertEqual(closed["status"], "Closed")
		self.assertIn("legal hold", frappe.db.get_value("Rights Request", req.name, "resolution"))

	# ------------------------------------------------------------ nomination, grievance

	def test_nominee_is_stored_encrypted(self):
		p = self.person()
		req = self.request("nomination", p)
		rights.add_nominee(req.name, "Suresh K. (fictional)", "brother", "9000088002")
		doc = frappe.get_doc("Data Principal", p.name)
		self.assertEqual(len(doc.nominees), 1)
		raw = frappe.db.get_value("Nominee", doc.nominees[0].name, ["nominee_name", "contact"])
		self.assertNotIn("Suresh", str(raw))
		self.assertNotIn("9000088002", str(raw))
		self.assertEqual(frappe.db.get_value("Rights Request", req.name, "status"), "Closed")

	def test_grievance_close_shows_board_route(self):
		frappe.db.set_single_value("Anumati Settings", "board_complaint_route", "Data Protection Board online portal")
		p = self.person()
		req = self.request("grievance", p)
		rights.close(req.name, "Called back and resolved.")
		self.assertIn("Data Protection Board", frappe.db.get_value("Rights Request", req.name, "resolution"))

	# ------------------------------------------------------------ SLA, replies, thread

	def test_overdue_flag_and_on_time(self):
		p = self.person()
		late = self.request("access", p, received_on=add_days(today(), -40))
		self.assertTrue(frappe.db.get_value("Rights Request", late.name, "overdue"))
		fresh = self.request("access", p)
		frappe.db.set_value("Rights Request", fresh.name, "sla_due", add_days(today(), -1))
		rights_core.mark_overdue()
		self.assertTrue(frappe.db.get_value("Rights Request", fresh.name, "overdue"))
		out = rights.close(late.name, "Done")
		self.assertFalse(out["on_time"])
		ok = self.request("grievance", p)
		self.assertTrue(rights.close(ok.name, "Done")["on_time"])
		self.assertTrue(frappe.db.get_value("Rights Request", ok.name, "closed_on"))

	def test_reply_needs_an_approved_template(self):
		p = self.person(phone=PHONE)
		req = self.request("grievance", p, channel="sms")
		with fake_post():
			self.assertTrue(rights.reply(req.name)["communication"])
			with self.assertRaises(frappe.ValidationError):
				rights.reply(req.name, "breach_notice")  # no approved template

	def test_inbound_sms_is_threaded_on_its_request(self):
		self.person(phone="9000088009")
		prov = frappe.get_doc("Channel Provider", "MSG91 test")
		out = channel.handle_sms(prov, "+91 90000 88009", "HELP")
		thread = self.thread(out["request"])
		self.assertEqual(len(thread), 1)
		self.assertEqual(thread[0].sent_or_received, "Received")
