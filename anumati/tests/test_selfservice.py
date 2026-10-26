"""Self-service page (/my-consent): sign-in, who can see whom, changing choices, receipts, rights requests and
the conversation with staff. MSG91 is mocked. Sample data is fictional."""

import random
import uuid
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from anumati import enforcement, inbox, selfservice
from anumati.api.v1 import rights
from anumati.tests.utils import make_event, make_principal, make_programme, make_purpose

PROG = "SSV"


def sms_ok():
	response = MagicMock(content=b"{}", status_code=200)
	response.json.return_value = {"type": "success", "request_id": f"req-{uuid.uuid4().hex[:8]}"}
	response.raise_for_status.return_value = None
	return patch("anumati.channels.msg91.requests.post", return_value=response)


def code(value="482913"):
	return patch("anumati.selfservice.secrets.randbelow", return_value=int(value))


def number():
	return "555" + "".join(random.choice("0123456789") for _ in range(7))


class TestSelfService(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_programme(PROG, "Self-service Test Programme")
		make_purpose(PROG, "screen", "Health screening", essential=1)
		make_purpose(PROG, "photos", "Photos and stories")
		make_purpose(PROG, "calls", "Follow-up calls")
		if not frappe.db.exists("Anumati Channel Provider", {"provider_type": "SMS", "enabled": 1}):
			frappe.get_doc({"doctype": "Anumati Channel Provider", "provider_name": "MSG91 self-service test", "provider_type": "SMS",
			                "provider": "MSG91", "enabled": 1, "api_key": "test-key"}).insert()
		if frappe.db.exists("Anumati Message Template", "otp-sms-en"):
			frappe.db.set_value("Anumati Message Template", "otp-sms-en", "approved", 1)
		else:
			frappe.get_doc({"doctype": "Anumati Message Template", "template_event": "otp", "channel": "sms", "language": "en",
			                "body": "Your OTP is ##OTP##", "approved": 1, "dlt_template_id": "otp-test",
			                "send_via": "SendOTP"}).insert()

	def setUp(self):
		frappe.flags.anumati_ss = None
		frappe.set_user("Administrator")
		self.phone = number()
		self.mother = make_principal(full_name="Sunita Devi (fictional)", phone=self.phone, birth_year=1988,
		                             preferred_language="en")
		self.child = make_principal(full_name="Meena Kumari (fictional)", is_minor=1, birth_year=2016)
		self.link = frappe.get_doc({"doctype": "Anumati Guardian Link", "principal": self.child.name, "guardian": self.mother.name,
		                            "guardian_type": "parent", "verification_method": "device_sms_otp"}).insert()
		self.event = make_event(self.mother.name, PROG, purposes_granted=["screen", "photos"], purposes_denied=["calls"])
		make_event(self.child.name, PROG, purposes_granted=["screen"], purposes_denied=[], guardian_link=self.link.name,
		           capture_mode="guardian_minor")
		self.stranger = make_principal(full_name="Asha Rani (fictional)", phone=number(), birth_year=1990)
		self.stranger_event = make_event(self.stranger.name, PROG, purposes_granted=["screen", "photos"], purposes_denied=[])

	def tearDown(self):
		frappe.flags.anumati_ss = None
		frappe.set_user("Administrator")

	def sign_in(self, phone=None):
		with sms_ok(), code():
			selfservice.start(phone or self.phone)
		return selfservice.verify(phone or self.phone, "482913")

	# ---------------------------------------------------------------- sign-in

	def test_a_code_goes_only_to_a_number_we_hold_and_the_answer_is_the_same(self):
		with sms_ok() as post, code():
			unknown = selfservice.start(number())
			self.assertEqual(post.call_count, 0, "no SMS to a number we don't hold")
			known = selfservice.start(self.phone)
			self.assertEqual(post.call_count, 1)
		self.assertEqual(unknown.keys(), known.keys())
		self.assertTrue(unknown["sent"] and known["sent"])
		self.assertNotIn(self.phone, frappe.as_json(known), "only a masked number comes back")

	def test_wrong_code_counts_tries_then_the_code_is_gone(self):
		with sms_ok(), code():
			selfservice.start(self.phone)
		for left in range(selfservice.MAX_TRIES - 1, -1, -1):
			self.assertEqual(selfservice.verify(self.phone, "000000"), {"signed_in": False, "tries_left": left})
		self.assertRaises(frappe.ValidationError, selfservice.verify, self.phone, "482913")

	def test_at_most_three_codes_per_number(self):
		with sms_ok(), code():
			for _ in range(selfservice.MAX_SENDS):
				selfservice.start(self.phone)
			self.assertRaises(frappe.ValidationError, selfservice.start, self.phone)

	def test_not_set_up_says_so(self):
		with patch("anumati.channels.can_send_codes", return_value=False):
			self.assertEqual(selfservice.start(self.phone), {"sent": False, "reason": "not_set_up"})

	def test_guardian_sees_themselves_and_their_child_only(self):
		home = self.sign_in()
		self.assertEqual([p["relation"] for p in home["people"]], ["self", "child"])
		self.assertEqual([p["name"].split()[0] for p in home["people"]], ["Sunita", "Meena"], "first names only")
		session = selfservice._get(selfservice._skey(frappe.flags.anumati_ss))
		self.assertEqual(session["people"], [self.mother.name, self.child.name])
		self.assertNotIn(self.stranger.name, session["people"])
		self.assertRaises(frappe.PermissionError, selfservice.overview, 2)

	def test_several_adults_on_one_phone_must_confirm_their_year_of_birth(self):
		shared = number()
		first = make_principal(full_name="Ravi Kumar (fictional)", phone=shared, birth_year=1970)
		second = make_principal(full_name="Kamla Devi (fictional)", phone=shared)
		home = self.sign_in(shared)
		self.assertEqual(len(home["choose"]), 2)
		self.assertNotIn("people", home)
		self.assertRaises(frappe.PermissionError, selfservice.overview, 0)
		i_first = [c["i"] for c in home["choose"] if c["name"].startswith("Ravi")][0]
		i_second = [c["i"] for c in home["choose"] if c["name"].startswith("Kamla")][0]
		self.assertRaises(frappe.ValidationError, selfservice.choose, i_first, 1971)
		self.assertRaises(frappe.ValidationError, selfservice.choose, i_second, 1975)  # no year on record
		home = selfservice.choose(i_first, 1970)
		session = selfservice._get(selfservice._skey(frappe.flags.anumati_ss))
		self.assertEqual(session["people"], [first.name])
		self.assertNotIn(second.name, session["people"])
		self.assertEqual(home["people"][0]["relation"], "self")

	def test_no_session_means_sign_in_again(self):
		for fn, args in ((selfservice.overview, (0,)), (selfservice.save_choices, (0, PROG)), (selfservice.leave, (0, PROG, 1)),
		                 (selfservice.ask, (0, "access")), (selfservice.write, (0, "RQ-0", "hi"))):
			self.assertRaises(selfservice.SignInError, fn, *args)
		self.assertEqual(selfservice.home(), {"signed_in": False})
		frappe.flags.anumati_ss = "made-up-token"
		self.assertRaises(selfservice.SignInError, selfservice.overview, 0)

	def test_sign_out_ends_the_session(self):
		self.sign_in()
		token = frappe.flags.anumati_ss
		selfservice.sign_out()
		frappe.flags.anumati_ss = token
		self.assertRaises(selfservice.SignInError, selfservice.overview, 0)

	# ---------------------------------------------------------------- choices

	def test_overview_shows_own_uses_history_and_no_numbers(self):
		self.sign_in()
		out = selfservice.overview(0)
		prog = out["programmes"][0]
		uses = {u["code"]: (u["status"], u["essential"]) for u in prog["uses"]}
		self.assertEqual(uses, {"screen": ("granted", 1), "photos": ("granted", 0), "calls": ("refused", 0)})
		self.assertTrue(prog["can_turn_on"])
		self.assertEqual(out["history"][0]["code"], self.event.short_code)
		self.assertNotIn(self.phone, frappe.as_json(out))
		self.assertNotIn(self.stranger_event.short_code, frappe.as_json(out))

	def test_turning_uses_off_and_on_records_signed_events(self):
		self.sign_in()
		out = selfservice.save_choices(0, PROG, turn_on=["calls"], turn_off=["photos"])
		self.assertEqual(len(out["codes"]), 2)
		states = enforcement.states_for(self.mother.name)
		self.assertEqual(states[f"{PROG}-photos"]["status"], "withdrawn")
		self.assertEqual(states[f"{PROG}-calls"]["status"], "granted")
		grant = frappe.get_all("Anumati Consent Event", {"principal": self.mother.name, "action": "grant", "channel": "web"},
		                       ["name", "verification_status", "capture_mode", "captured_by"])[0]
		self.assertEqual((grant.verification_status, grant.capture_mode), ("confirmed", "self_digital"))
		self.assertTrue(frappe.db.exists("Anumati Verification Attempt", {"consent_event": grant.name, "result": "confirmed"}))
		closed = frappe.get_all("Anumati Rights Request", {"matched_principal": self.mother.name, "channel": "web"},
		                        ["request_type", "status", "raised_by_role"])
		self.assertEqual([(r.request_type, r.status, r.raised_by_role) for r in closed],
		                 [("withdrawal", inbox.CLOSED, "by_self")], "every withdrawal is listed in the inbox, done")

	def test_essential_use_never_toggles(self):
		self.sign_in()
		self.assertRaises(frappe.ValidationError, selfservice.save_choices, 0, PROG, turn_off=["screen"])

	def test_guardian_turns_on_a_use_for_their_child_with_the_guardian_link(self):
		self.sign_in()
		selfservice.save_choices(1, PROG, turn_on=["photos"])
		event = frappe.get_all("Anumati Consent Event", {"principal": self.child.name, "channel": "web"},
		                       ["guardian_link", "capture_mode"])[0]
		self.assertEqual((event.guardian_link, event.capture_mode), (self.link.name, "guardian_minor"))

	def test_leaving_stops_every_use_and_ends_the_relationship(self):
		self.sign_in()
		self.assertRaises(frappe.ValidationError, selfservice.leave, 0, PROG, 0)
		out = selfservice.leave(0, PROG, 1)
		self.assertTrue(out["programmes"][0]["left"])
		self.assertFalse(out["programmes"][0]["can_turn_on"])
		self.assertTrue(frappe.db.get_value("Anumati Data Principal", self.mother.name, "relationship_ended_on"))
		self.assertRaises(frappe.ValidationError, selfservice.save_choices, 0, PROG, turn_on=["photos"])

	def test_a_programme_they_are_not_in_is_refused(self):
		make_programme("SSX", "Another Programme")
		self.sign_in()
		self.assertRaises(frappe.PermissionError, selfservice.save_choices, 0, "SSX", turn_off=["photos"])

	# ---------------------------------------------------------------- receipt code sign-in

	def test_receipt_code_and_year_can_only_turn_off(self):
		self.assertRaises(frappe.ValidationError, selfservice.code_login, self.event.short_code, 1999)
		home = selfservice.code_login(self.event.short_code.replace("AN-", "").lower(), 1988)
		self.assertEqual(home["mode"], "code")
		self.assertEqual(len(home["people"]), 1, "a slip never opens the children")
		out = selfservice.overview(0)
		self.assertFalse(out["programmes"][0]["can_turn_on"])
		self.assertRaises(frappe.ValidationError, selfservice.save_choices, 0, PROG, turn_on=["calls"])
		selfservice.save_choices(0, PROG, turn_off=["photos"])
		self.assertEqual(enforcement.states_for(self.mother.name)[f"{PROG}-photos"]["status"], "withdrawn")

	def test_receipt_code_tries_are_limited(self):
		for _ in range(selfservice.MAX_TRIES):
			self.assertRaises(frappe.ValidationError, selfservice.code_login, self.event.short_code, 1900)
		self.assertRaises(frappe.ValidationError, selfservice.code_login, self.event.short_code, 1988)

	# ---------------------------------------------------------------- receipts

	def test_receipt_is_their_own(self):
		self.sign_in()
		html = selfservice.receipt_file(self.event.name, as_pdf=False)
		self.assertIn(self.event.short_code, html)
		self.assertRaises(frappe.PermissionError, selfservice.receipt, 0, self.stranger_event.name)

	# ---------------------------------------------------------------- requests and conversation

	def test_rights_request_and_the_conversation_with_staff(self):
		self.sign_in()
		out = selfservice.ask(0, "access", "Please send me what you hold")
		request = out["request"]
		doc = frappe.get_doc("Anumati Rights Request", request)
		self.assertEqual((doc.request_type, doc.channel, doc.raised_by_role, doc.status, doc.matched_principal),
		                 ("access", "web", "by_self", inbox.NEW, self.mother.name))
		self.assertRaises(frappe.ValidationError, selfservice.ask, 0, "withdrawal")

		frappe.set_user("Administrator")
		rights.reply(request, "Which programme is this about?", "question")
		self.assertEqual(frappe.db.get_value("Anumati Rights Request", request, "status"), inbox.WAITING_PERSON)
		out = selfservice.write(0, request, "The health camp")
		self.assertEqual(frappe.db.get_value("Anumati Rights Request", request, "status"), inbox.WORKING)
		rights.reply(request, "Your summary is attached to the SMS we sent today.", "answer")
		doc.reload()
		self.assertEqual(doc.status, inbox.ANSWERED)
		self.assertIn("summary", doc.answer)
		thread = selfservice.overview(0)["requests"][0]["messages"]
		self.assertEqual([m["from"] for m in thread], ["you", "office", "you", "office"])
		self.assertNotIn("Administrator", frappe.as_json(thread), "the person never sees staff names")

	def test_cannot_write_on_someone_elses_request(self):
		frappe.set_user("Administrator")
		other = frappe.get_doc({"doctype": "Anumati Rights Request", "request_type": "access", "channel": "email",
		                        "matched_principal": self.stranger.name}).insert()
		self.sign_in()
		self.assertRaises(frappe.PermissionError, selfservice.write, 0, other.name, "hello")

	def test_staff_reply_needs_write_permission_and_a_known_kind(self):
		self.sign_in()
		request = selfservice.ask(0, "correction")["request"]
		frappe.set_user("Administrator")
		self.assertRaises(frappe.ValidationError, rights.reply, request, "hi", "shout")
		self.assertRaises(frappe.ValidationError, rights.reply, request, "  ", "update")
		frappe.set_user("Guest")
		self.assertRaises(frappe.PermissionError, rights.reply, request, "hi", "update")
