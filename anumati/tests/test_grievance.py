"""Grievances: where they come from, who can see them, the conversation and outcome, "did this solve it?",
the DPO at day 15, moving between grievances and rights requests, the register, and the self-service page.
Sample data is fictional."""

import base64
import random
import uuid
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from anumati import evidence, grievance, inbox, selfservice
from anumati.anumati.report.grievance_register import grievance_register
from anumati.api.v1 import channel, rights
from anumati.api.v1 import grievance as api
from anumati.tests.utils import call_webhook, make_event, make_principal, make_programme, make_purpose

PROG = "GRV"
SECRET = "grievance-test-inbound-secret"
PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\0" * 64).decode()


def number():
	return "555" + "".join(random.choice("0123456789") for _ in range(7))


def user_with(role):
	email = f"grievance.{frappe.scrub(role)}.{uuid.uuid4().hex[:6]}@example.com"
	frappe.get_doc({"doctype": "User", "email": email, "first_name": "Test", "send_welcome_email": 0,
	                "roles": [{"role": role}]}).insert(ignore_permissions=True)
	return email


def sms_ok():
	response = MagicMock(content=b"{}", status_code=200)
	response.json.return_value = {"type": "success", "request_id": "req-1"}
	response.raise_for_status.return_value = None
	return patch("anumati.channels.msg91.requests.post", return_value=response)


class TestGrievance(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_programme(PROG, "Grievance Test Programme")
		make_purpose(PROG, "screen", "Health screening", essential=1)
		make_purpose(PROG, "photos", "Photos and stories")
		if not frappe.db.exists("Channel Provider", "MSG91 grievance test"):
			frappe.get_doc({"doctype": "Channel Provider", "provider_name": "MSG91 grievance test", "provider_type": "SMS",
			                "provider": "MSG91", "enabled": 1, "api_key": "test-key", "webhook_secret": SECRET}).insert()
		if frappe.db.exists("Message Template", "otp-sms-en"):
			frappe.db.set_value("Message Template", "otp-sms-en", "approved", 1)
		else:
			frappe.get_doc({"doctype": "Message Template", "template_event": "otp", "channel": "sms", "language": "en",
			                "body": "Your OTP is ##OTP##", "approved": 1, "dlt_template_id": "otp-test",
			                "send_via": "SendOTP"}).insert()
		cls.dpo = user_with("Anumati DPO")
		cls.operator = user_with("Anumati Operator")
		cls.worker = user_with("Anumati Field Worker")
		frappe.db.set_single_value("Anumati Settings", "dpo_email", cls.dpo)

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.flags.anumati_ss = None
		self.phone = number()
		self.person = make_principal(full_name="Kamla Bai (fictional)", phone=self.phone, birth_year=1979)
		self.event = make_event(self.person.name, PROG, purposes_granted=["screen", "photos"], purposes_denied=[])
		self.other = make_principal(full_name="Gita Rani (fictional)", phone=number(), birth_year=1985)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.flags.anumati_ss = None

	def new(self, category="used_without_consent", **kw):
		return grievance.create(category, "web", self.person.name, description="My photo was used", **kw)

	def sign_in(self):
		with sms_ok(), patch("anumati.selfservice.secrets.randbelow", return_value=246810):
			selfservice.start(self.phone)
		return selfservice.verify(self.phone, "246810")

	# ---------------------------------------------------------------- where they come from

	def test_complaints_from_the_field_app_and_sms_are_grievances_not_rights_requests(self):
		out = rights.submit("grievance", "field_worker", principal_ref=self.person.principal_ref, payload="Calls continued")
		self.assertTrue(out["request"].startswith("GR-"))
		doc = frappe.get_doc("Grievance", out["request"])
		self.assertEqual((doc.category, doc.raised_by_role, doc.matched_principal), ("something_else", "by_field_worker", self.person.name))
		self.assertFalse(frappe.db.exists("Rights Request", {"matched_principal": self.person.name}))
		sms = call_webhook(channel.inbound_sms, provider="MSG91 grievance test", token=SECRET, sender=self.phone, message="HELP please call")
		self.assertEqual(sms["outcome"], "grievance")
		self.assertEqual(frappe.db.get_value("Grievance", sms["request"], "matched_principal"), self.person.name)

	def test_grievance_api_checks_the_category(self):
		out = api.submit("did_not_stop", "field_worker", principal_ref=self.person.principal_ref, description="Still calling")
		self.assertEqual(frappe.db.get_value("Grievance", out["grievance"], "category"), "did_not_stop")
		self.assertRaises(frappe.ValidationError, api.submit, "made_up", "field_worker")

	def test_reply_by_is_thirty_days_and_the_request_must_be_theirs(self):
		doc = self.new()
		self.assertEqual(frappe.utils.date_diff(doc.sla_due, doc.received_on), 30)
		theirs = frappe.get_doc({"doctype": "Rights Request", "request_type": "access", "channel": "email",
		                         "matched_principal": self.other.name}).insert()
		self.assertRaises(frappe.ValidationError, self.new, "request_not_answered", about_request=theirs.name)

	# ---------------------------------------------------------------- who sees them

	def test_staff_behaviour_goes_to_the_dpo_only(self):
		doc = self.new("staff_behaviour")
		self.assertEqual(doc.assigned_to, self.dpo)
		self.assertTrue(doc.dpo_since)
		plain = self.new()
		frappe.set_user(self.operator)
		self.assertFalse(frappe.has_permission("Grievance", "read", doc=doc.name))
		names = frappe.get_list("Grievance", pluck="name", limit_page_length=0)
		self.assertNotIn(doc.name, names)
		self.assertIn(plain.name, names)
		frappe.set_user(self.dpo)
		self.assertTrue(frappe.has_permission("Grievance", "read", doc=doc.name))
		self.assertIn(doc.name, frappe.get_list("Grievance", pluck="name", limit_page_length=0))

	def test_field_worker_sees_only_what_they_raised(self):
		other = self.new()
		frappe.set_user(self.worker)
		mine = api.submit("wrong_details", "field_worker", principal_ref=self.person.principal_ref, description="Name spelt wrong")
		names = frappe.get_list("Grievance", pluck="name", limit_page_length=0)
		self.assertEqual(names, [mine["grievance"]])
		self.assertFalse(frappe.has_permission("Grievance", "read", doc=other.name))

	# ---------------------------------------------------------------- conversation and outcome

	def test_final_answer_needs_an_outcome_and_the_person_can_push_back_once(self):
		doc = self.new()
		api.reply(doc.name, "Which month was it?", "question")
		self.assertEqual(frappe.db.get_value("Grievance", doc.name, "status"), inbox.WAITING_PERSON)
		self.assertRaises(frappe.ValidationError, api.reply, doc.name, "Removed it", "answer")
		api.reply(doc.name, "We removed the photo.", "answer", "put_right")
		doc.reload()
		self.assertEqual((doc.status, doc.outcome, doc.answer), (inbox.ANSWERED, "put_right", "We removed the photo."))

		grievance.respond(doc, solved=False)
		doc.reload()
		self.assertEqual((doc.status, doc.person_says, doc.assigned_to), (inbox.WORKING, "not_happy", self.dpo))
		self.assertTrue(doc.dpo_since)
		api.reply(doc.name, "It is also gone from the printed newsletter now.", "answer", "put_right")
		doc.reload()
		self.assertFalse(grievance.can_say_not_happy(doc))
		self.assertRaises(frappe.ValidationError, grievance.respond, doc, False)
		grievance.respond(doc, solved=True)
		self.assertEqual(frappe.db.get_value("Grievance", doc.name, "status"), inbox.CLOSED)
		self.assertRaises(frappe.ValidationError, api.reply, doc.name, "More", "update")

	# ---------------------------------------------------------------- daily

	def test_no_answer_in_fifteen_days_goes_to_the_dpo_and_quiet_answers_close(self):
		slow = self.new()
		slow.db_set("received_on", add_to_date(now_datetime(), days=-16))
		answered = self.new()
		api.reply(answered.name, "Done", "answer", "no_problem_found")
		frappe.db.set_value("Grievance", answered.name, "answered_on", add_to_date(now_datetime(), days=-31))
		grievance.daily()
		self.assertEqual(frappe.db.get_value("Grievance", slow.name, "assigned_to"), self.dpo)
		self.assertTrue(frappe.db.get_value("Grievance", slow.name, "dpo_since"))
		self.assertEqual(frappe.db.get_value("Grievance", answered.name, "status"), inbox.CLOSED)

	# ---------------------------------------------------------------- moving

	def test_move_between_rights_requests_and_grievances(self):
		request = frappe.get_doc({"doctype": "Rights Request", "request_type": "access", "channel": "email",
		                          "matched_principal": self.person.name, "raw_payload": "You shared my number!"}).insert()
		frappe.get_doc({"doctype": "Communication", "communication_type": "Communication", "communication_medium": "Other",
		                "sent_or_received": "Received", "content": "You shared my number!", "subject": "Complaint",
		                "reference_doctype": "Rights Request", "reference_name": request.name}).insert(ignore_permissions=True)
		moved = api.move_from_request(request.name)["grievance"]
		self.assertEqual(frappe.db.get_value("Rights Request", request.name, "status"), inbox.CLOSED)
		self.assertTrue(frappe.db.exists("Communication", {"reference_doctype": "Grievance", "reference_name": moved}))
		back = api.move_to_request(moved, "erasure")["request"]
		self.assertEqual(frappe.db.get_value("Rights Request", back, "request_type"), "erasure")
		self.assertEqual(frappe.db.get_value("Grievance", moved, "status"), inbox.CLOSED)

	def test_old_grievance_requests_move_over_on_migrate(self):
		from anumati.patches import grievances_from_requests

		request = frappe.get_doc({"doctype": "Rights Request", "request_type": "access", "channel": "sms",
		                          "matched_principal": self.person.name, "raw_payload": "HELP"}).insert()
		frappe.db.set_value("Rights Request", request.name, "request_type", "grievance")
		grievances_from_requests.execute()
		self.assertFalse(frappe.db.exists("Rights Request", request.name))
		moved = frappe.get_all("Grievance", {"matched_principal": self.person.name, "raw_payload": "HELP"}, pluck="name")
		self.assertEqual(len(moved), 1)

	# ---------------------------------------------------------------- register

	def test_register_counts_by_category(self):
		a = self.new("did_not_stop")
		api.reply(a.name, "Stopped now", "answer", "put_right")
		self.new("did_not_stop")
		columns, data = grievance_register.execute({})
		row = next(r for r in data if r["category"] == frappe._("did_not_stop"))
		self.assertGreaterEqual(row["received"], 2)
		self.assertGreaterEqual(row["answered"], 1)
		self.assertNotIn("Kamla", frappe.as_json(data), "totals only, never a person")

	# ---------------------------------------------------------------- self-service page

	def test_self_service_grievance_with_a_photo_and_the_answer(self):
		self.sign_in()
		self.assertRaises(frappe.ValidationError, selfservice.complain, 0, "did_not_stop", "")
		self.assertRaises(frappe.ValidationError, selfservice.complain, 0, "request_not_answered", "No reply")
		theirs = frappe.get_doc({"doctype": "Rights Request", "request_type": "access", "channel": "email",
		                         "matched_principal": self.other.name}).insert(ignore_permissions=True)
		self.assertRaises(frappe.PermissionError, selfservice.complain, 0, "request_not_answered", "No reply",
		                  about_request=theirs.name)
		self.assertRaises(frappe.ValidationError, selfservice.complain, 0, "did_not_stop", "Still calling",
		                  photo="data:text/plain;base64," + base64.b64encode(b"hello").decode())
		out = selfservice.complain(0, "did_not_stop", "Still calling after STOP", photo="data:image/png;base64," + PNG)
		name = out["grievance"]
		doc = frappe.get_doc("Grievance", name)
		self.assertEqual((doc.channel, doc.raised_by_role, doc.matched_principal), ("web", "by_self", self.person.name))
		file = frappe.get_doc("File", {"attached_to_doctype": "Grievance", "attached_to_name": name})
		self.assertTrue(file.is_private)
		with open(file.get_full_path(), "rb") as fh:
			self.assertTrue(fh.read().startswith(evidence.MAGIC), "the photo is encrypted on disk")

		frappe.set_user("Administrator")
		api.reply(name, "We have stopped the calls.", "answer", "put_right")
		card = next(r for r in selfservice.overview(0)["requests"] if r["id"] == name)
		self.assertEqual(card["outcome"], frappe._(grievance.OUTCOME_FOR_PERSON["put_right"]))
		self.assertTrue(card["can_respond"] and card["can_say_not_happy"] and card["board_route"])
		self.assertEqual([m["from"] for m in card["messages"]], ["you", "office"])
		out = selfservice.respond(0, name, 0)
		card = next(r for r in out["requests"] if r["id"] == name)
		self.assertTrue(card["with_dpo"])
		self.assertRaises(frappe.PermissionError, selfservice.respond, 0, self.other_grievance(), 1)

	def other_grievance(self):
		return grievance.create("something_else", "web", self.other.name, description="Not mine").name
