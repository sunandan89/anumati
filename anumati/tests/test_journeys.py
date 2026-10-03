"""Who may consent and what each field journey must carry (design A1-A4), extra questions about the person
(profile questions), and renewal when a child turns 18. All sample data is fictional."""

import datetime
import uuid

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from anumati import enforcement, profile
from anumati.api.schema import SchemaError
from anumati.api.v1 import consent, notice, notifications, principal
from anumati.api.v1.consent import ConsentRequestError
from anumati.tests.utils import ensure_language, make_principal, make_programme, make_purpose

PROG = "JRN"


def uid():
	return str(uuid.uuid4())


def publish_notice(programme, purposes, full_text):
	if not frappe.db.exists("Data Category", "Health readings"):
		frappe.get_doc({"doctype": "Data Category", "category_name": "Health readings"}).insert()
	for purpose in purposes:
		if not frappe.db.exists("ROPA Entry", {"purpose": purpose, "status": "Approved"}):
			ropa = frappe.get_doc({"doctype": "ROPA Entry", "purpose": purpose, "retention": "24 months",
			                       "safeguards": "Encrypted", "data_categories": [{"data_category": "Health readings"}]}).insert()
			apply_workflow(ropa, "Approve")
	doc = frappe.get_doc({
		"doctype": "Notice Template", "programme": programme, "version": f"1.0.{frappe.db.count('Notice Template')}",
		"summary": "We screen your health.", "full_text": full_text, "purposes": [{"purpose": p} for p in purposes],
		"withdrawal_methods": "SMS STOP", "rights_text": "Access, correction", "board_complaint_route": "Data Protection Board",
		"dpo_contact": "DPO (fictional)", "security_summary": "Encrypted",
	}).insert()
	return apply_workflow(doc, "Publish")


class TestJourneys(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		profile.ensure_library()
		make_programme(PROG, "Journey Test Programme")
		cls.screen = make_purpose(PROG, "screen", "Health screening", essential=1)
		cls.follow = make_purpose(PROG, "follow", "Follow-up calls", needs_phone=1)
		cls.notice = publish_notice(PROG, [cls.screen, cls.follow],
		                            "<p>Name, <b>age</b>, occupation and test results. Kept for 24 months.</p>").name

	def grant(self, ref, **kw):
		return consent.record({
			"event_uuid": uid(), "principal_ref": ref, "programme": PROG, "purposes_granted": ["screen", "follow"],
			"capture_mode": kw.pop("capture_mode", "self_worker_device"), "channel": "app", "device_id": "FW-JRN-01",
			"device_time": "2026-10-01 10:00:00", **kw,
		})

	def link(self, person, **kw):
		guardian = make_principal()
		return frappe.get_doc({"doctype": "Guardian Link", "principal": person.name, "guardian": guardian.name,
		                       "verification_method": "device_sms_otp", **kw}).insert().name

	# -- A1: someone who needs help to read -----------------------------------

	def test_needs_help_to_read_needs_a_witness(self):
		p = make_principal(needs_assistance=1)
		self.assertRaises(ConsentRequestError, self.grant, p.principal_ref, capture_mode="assisted_verbal")
		art = self.grant(p.principal_ref, capture_mode="assisted_verbal", witness="ASHA worker (sample)")
		self.assertTrue(art["hash"])

	def test_refusal_needs_no_witness(self):
		p = make_principal(needs_assistance=1)
		art = self.grant(p.principal_ref, action="refuse", purposes_granted=[], purposes_denied=["follow"])
		self.assertEqual(art["action"], "refuse")

	def test_reads_without_phone_needs_no_witness(self):
		p = make_principal(no_phone=1)
		self.assertTrue(self.grant(p.principal_ref, verification_method="evidence_only")["hash"])

	# -- A2/A3: children --------------------------------------------------------

	def test_parent_needs_no_order_number(self):
		child = make_principal(is_minor=1)
		art = self.grant(child.principal_ref, capture_mode="guardian_minor",
		                 guardian_link=self.link(child, guardian_type="parent", relation="Mother"))
		self.assertTrue(art["hash"])

	def test_other_guardian_of_a_child_needs_the_order_number(self):
		child = make_principal(is_minor=1)
		bare = self.link(child, guardian_type="legal_guardian")
		self.assertRaises(ConsentRequestError, self.grant, child.principal_ref, capture_mode="guardian_minor", guardian_link=bare)
		ordered = self.link(child, guardian_type="legal_guardian", authority_ref="GO-123/2026 (sample)")
		self.assertTrue(self.grant(child.principal_ref, capture_mode="guardian_minor", guardian_link=ordered)["hash"])

	def test_guardian_link_must_belong_to_the_person(self):
		child, other = make_principal(is_minor=1), make_principal(is_minor=1)
		self.assertRaises(ConsentRequestError, self.grant, child.principal_ref, capture_mode="guardian_minor",
		                  guardian_link=self.link(other, guardian_type="parent"))

	# -- A4: adults who can't decide alone ------------------------------------

	def test_adult_who_cant_decide_alone_needs_an_appointed_guardian_with_an_order(self):
		p = make_principal(pwd_guarded=1)
		self.assertRaises(ConsentRequestError, self.grant, p.principal_ref, capture_mode="guardian_pwd")
		self.assertRaises(ConsentRequestError, self.grant, p.principal_ref, capture_mode="guardian_pwd",
		                  guardian_link=self.link(p, guardian_type="parent", authority_ref="X-1"))
		self.assertRaises(ConsentRequestError, self.grant, p.principal_ref, capture_mode="guardian_pwd",
		                  guardian_link=self.link(p, guardian_type="committee"))
		art = self.grant(p.principal_ref, capture_mode="guardian_pwd",
		                 guardian_link=self.link(p, guardian_type="committee", relation="Sibling",
		                                         authority_ref="LLC/2026/0412 (sample)"))
		self.assertTrue(art["hash"])

	def test_coordinator_is_told_without_personal_data(self):
		manager = "jrn.manager@example.com"
		if not frappe.db.exists("User", manager):
			user = frappe.get_doc({"doctype": "User", "email": manager, "first_name": "Coordinator (sample)",
			                       "send_welcome_email": 0})
			user.insert(ignore_permissions=True)
			user.add_roles("Anumati Programme Manager")
		before = frappe.db.count("Notification Log", {"for_user": manager})
		out = notifications.guardian_needed(PROG)
		self.assertGreaterEqual(out["told"], 1)
		self.assertEqual(frappe.db.count("Notification Log", {"for_user": manager}), before + 1)
		log = frappe.get_last_doc("Notification Log", {"for_user": manager})
		self.assertEqual(log.document_name, PROG)

	# -- purposes that need a phone, translated names ---------------------------

	def test_notice_says_which_uses_need_a_phone_and_serves_translated_names(self):
		ensure_language("hi", "Hindi")
		if not frappe.db.exists("Notice Translation", {"notice": self.notice, "language": "hi"}):
			frappe.get_doc({
				"doctype": "Notice Translation", "notice": self.notice, "language": "hi", "summary": "हम जाँच करते हैं।",
				"reviewer": "Administrator",
				"purposes": [{"purpose": self.follow, "purpose_title": "फ़ॉलो-अप कॉल", "description": "फ़ोन पर हाल पूछना"}],
			}).insert()
		out = notice.get_active(PROG, language="hi")
		flags = {p["code"]: p["needs_phone"] for p in out["purposes"]}
		self.assertEqual(flags, {"screen": 0, "follow": 1})
		self.assertEqual(out["translation"]["purposes"],
		                 [{"code": "follow", "purpose_title": "फ़ॉलो-अप कॉल", "description": "फ़ोन पर हाल पूछना"}])

	# -- extra questions ---------------------------------------------------------

	def test_library_has_about_twenty_questions_and_flags_sensitive_ones(self):
		self.assertGreaterEqual(frappe.db.count("Profile Question", {"is_standard": 1}), 20)
		self.assertTrue(frappe.db.get_value("Profile Question", "social_category", "is_sensitive"))
		self.assertFalse(frappe.db.get_value("Profile Question", "age", "is_sensitive"))

	def test_questions_are_off_by_default_and_only_ones_the_notice_lists_can_be_switched_on(self):
		prog = frappe.get_doc("Programme", PROG)
		prog.set("profile_questions", [])
		prog.save()
		self.assertEqual(notice.get_active(PROG)["profile_questions"], [])
		prog.append("profile_questions", {"question": "education"})
		self.assertRaises(frappe.ValidationError, prog.save)
		prog.reload()
		prog.append("profile_questions", {"question": "age", "required": 1})
		prog.append("profile_questions", {"question": "occupation"})
		prog.save()
		questions = notice.get_active(PROG, language="hi")["profile_questions"]
		self.assertEqual([q["code"] for q in questions], ["age", "occupation"])
		self.assertEqual(questions[0]["required"], 1)
		self.assertEqual(questions[1]["question"], "काम / पेशा")
		self.assertEqual(questions[1]["options"][0]["value"], "Farming or farm labour")

	def test_upsert_stores_answers_and_checks_them(self):
		ref = f"JRN-{uuid.uuid4().hex[:8]}"
		principal.upsert(ref, full_name="Kamla D. (fictional)", programme=PROG,
		                 profile={"age": "41", "occupation": "Daily wage work"})
		doc = frappe.get_doc("Data Principal", {"principal_ref": ref})
		self.assertEqual({a.question: a.answer for a in doc.profile_answers}, {"age": "41", "occupation": "Daily wage work"})
		principal.upsert(ref, programme=PROG, profile={"age": "42"})
		doc.reload()
		self.assertEqual(len(doc.profile_answers), 2)
		self.assertRaises(frappe.ValidationError, principal.upsert, ref, profile={"occupation": "Astronaut"})
		self.assertRaises(frappe.ValidationError, principal.upsert, ref, profile={"age": "forty"})
		self.assertRaises(SchemaError, principal.upsert, ref, profile={"Bad Code!": "1"})

	# -- birth year and renewal at 18 -------------------------------------------

	def test_birth_year_marks_a_child_and_the_day_they_turn_18(self):
		year = getdate(today()).year - 10
		ref = f"JRN-{uuid.uuid4().hex[:8]}"
		principal.upsert(ref, full_name="Child (fictional)", birth_year=year)
		doc = frappe.get_doc("Data Principal", {"principal_ref": ref})
		self.assertTrue(doc.is_minor)
		self.assertEqual(getdate(doc.adult_on), datetime.date(year + 18, 12, 31))

	def test_turning_18_needs_the_persons_own_consent(self):
		child = make_principal(is_minor=1)
		self.grant(child.principal_ref, capture_mode="guardian_minor", guardian_link=self.link(child, guardian_type="parent"))
		frappe.db.set_value("Programme", PROG, "allow_processing_before_confirm", 1)
		consent.record({"event_uuid": uid(), "principal_ref": child.principal_ref, "programme": PROG, "action": "renew",
		                "purposes_granted": ["follow"], "verification_status": "confirmed", "channel": "app",
		                "guardian_link": self.link(child, guardian_type="parent")})
		frappe.db.set_value("Data Principal", child.name, "adult_on", add_days(today(), -1))
		enforcement.flag_new_adults()
		self.assertTrue(frappe.db.get_value("Data Principal", child.name, "renewal_due"))
		verdict = consent.check(child.principal_ref, "follow", programme=PROG)
		self.assertFalse(verdict["allow"])
		self.assertEqual(verdict["status"], "renewal_due")
		# Now 18, they consent themselves: no guardian, and they are an adult record from here on.
		self.grant(child.principal_ref, verification_status="confirmed")
		flags = frappe.db.get_value("Data Principal", child.name, ["is_minor", "renewal_due"], as_dict=True)
		self.assertEqual((flags.is_minor, flags.renewal_due), (0, 0))
		self.assertTrue(consent.check(child.principal_ref, "follow", programme=PROG)["allow"])

	def test_report_shows_totals_only(self):
		from anumati.anumati.report.profile_answer_totals.profile_answer_totals import execute

		for _ in range(5):
			principal.upsert(f"JRN-{uuid.uuid4().hex[:8]}", programme=PROG, profile={"occupation": "Homemaker"})
		principal.upsert(f"JRN-{uuid.uuid4().hex[:8]}", programme=PROG, profile={"occupation": "Salaried job"})
		columns, data = execute({"programme": PROG, "question": "occupation"})
		self.assertEqual([c["fieldname"] for c in columns], ["question", "answer", "people"])
		counts = {r["answer"]: r["people"] for r in data}
		self.assertGreaterEqual(counts["Homemaker"], 5)
		self.assertEqual(counts["Salaried job"], "fewer than 5")
