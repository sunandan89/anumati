"""Which notices a field worker (and their phone's SDK sync) can read: published notices for their own
programmes, and the translations of those notices. Sample data is fictional."""

import frappe
from frappe.tests.utils import FrappeTestCase

from anumati.tests.test_journeys import publish_notice
from anumati.tests.utils import ensure_language, make_programme, make_purpose

WORKER = "notice.worker@example.com"
ANY_WORKER = "notice.anyworker@example.com"
OPERATOR = "notice.operator@example.com"


def user(email, role):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": "Notice", "last_name": role.split()[-1],
		                "user_type": "System User", "send_welcome_email": 0, "roles": [{"role": role}]}).insert()
	return email


def translate(notice):
	ensure_language("hi", "Hindi")
	name = f"{notice}-hi"
	if not frappe.db.exists("Anumati Notice Translation", name):
		frappe.get_doc({"doctype": "Anumati Notice Translation", "notice": notice, "language": "hi",
		                "summary": "Swasthya jaanch"}).insert()
	return name


class TestNoticeAccess(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		user(WORKER, "Anumati Field Worker")
		user(ANY_WORKER, "Anumati Field Worker")
		user(OPERATOR, "Anumati Operator")
		for code in ("NA1", "NA2"):
			make_programme(code, f"Notice Access {code}")
		cls.mine = publish_notice("NA1", [make_purpose("NA1", "screen", "Health screening")], "Full text").name
		cls.other = publish_notice("NA2", [make_purpose("NA2", "screen", "Health screening")], "Full text").name
		cls.draft = frappe.get_doc({
			"doctype": "Anumati Notice Template", "programme": "NA1", "version": "9.9.9", "summary": "Not ready",
			"purposes": [{"purpose": "NA1-screen"}], "withdrawal_methods": "SMS STOP", "rights_text": "Access, correction",
			"board_complaint_route": "Data Protection Board", "dpo_contact": "DPO (fictional)", "security_summary": "Encrypted",
		}).insert().name
		cls.t_mine, cls.t_other, cls.t_draft = (translate(n) for n in (cls.mine, cls.other, cls.draft))
		if not frappe.db.exists("User Permission", {"user": WORKER, "allow": "Anumati Programme", "for_value": "NA1"}):
			frappe.get_doc({"doctype": "User Permission", "user": WORKER, "allow": "Anumati Programme",
			                "for_value": "NA1"}).insert()

	def tearDown(self):
		frappe.set_user("Administrator")

	def visible(self, doctype, names):
		return set(frappe.get_list(doctype, {"name": ("in", names)}, pluck="name"))

	def test_a_field_worker_sees_only_published_notices_for_their_programmes(self):
		frappe.set_user(WORKER)
		self.assertEqual(self.visible("Anumati Notice Template", [self.mine, self.other, self.draft]), {self.mine})
		self.assertEqual(self.visible("Anumati Notice Translation", [self.t_mine, self.t_other, self.t_draft]), {self.t_mine})
		self.assertTrue(frappe.has_permission("Anumati Notice Template", "read", doc=self.mine))
		self.assertFalse(frappe.has_permission("Anumati Notice Template", "read", doc=self.draft))
		self.assertFalse(frappe.has_permission("Anumati Notice Template", "read", doc=self.other))
		self.assertFalse(frappe.has_permission("Anumati Notice Translation", "read", doc=self.t_draft))
		self.assertFalse(frappe.has_permission("Anumati Notice Translation", "read", doc=self.t_other))

	def test_a_field_worker_without_programme_limits_still_never_sees_drafts(self):
		frappe.set_user(ANY_WORKER)
		self.assertEqual(self.visible("Anumati Notice Template", [self.mine, self.other, self.draft]), {self.mine, self.other})
		self.assertEqual(self.visible("Anumati Notice Translation", [self.t_mine, self.t_other, self.t_draft]),
		                 {self.t_mine, self.t_other})

	def test_staff_see_drafts_too(self):
		frappe.set_user(OPERATOR)
		self.assertEqual(self.visible("Anumati Notice Template", [self.mine, self.other, self.draft]),
		                 {self.mine, self.other, self.draft})
		self.assertTrue(frappe.has_permission("Anumati Notice Translation", "read", doc=self.t_draft))
