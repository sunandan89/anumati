"""Rights requests and grievances created directly (REST or the Frappe Mobile SDK's sync) by a field
worker: the sender can't fill in what only staff decide, and a retried push is filed once.
Sample data is fictional."""

import uuid

import frappe
from frappe.client import insert as client_insert
from frappe.tests import IntegrationTestCase
from frappe.utils import get_datetime, now_datetime

from anumati.tests.utils import make_principal

WORKER = "intake.worker@example.com"
OPERATOR = "intake.operator@example.com"


def user(email, role):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": "Intake", "last_name": role.split()[-1],
		                "user_type": "System User", "send_welcome_email": 0, "roles": [{"role": role}]}).insert()
	return email


class TestIntake(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		user(WORKER, "Anumati Field Worker")
		user(OPERATOR, "Anumati Operator")

	def setUp(self):
		frappe.set_user("Administrator")
		self.p = make_principal()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_a_field_worker_cannot_file_a_request_already_closed_or_answered(self):
		frappe.set_user(WORKER)
		mid = str(uuid.uuid4())
		out = client_insert({
			"doctype": "Anumati Rights Request", "mobile_uuid": mid, "request_type": "access", "channel": "field_worker",
			"matched_principal": self.p.name, "raw_payload": "Wants to see her data",
			"status": "request_closed", "received_on": "2020-01-01 00:00:00", "sla_due": "2099-12-31",
			"assigned_to": "Administrator", "answer": "Done", "resolution": "Closed by the worker",
		})
		doc = frappe.get_doc("Anumati Rights Request", out["name"])
		self.assertEqual(doc.status, "new_request")
		self.assertGreater(get_datetime(doc.received_on), get_datetime("2026-01-01"))
		self.assertLessEqual(get_datetime(doc.received_on), now_datetime())
		self.assertNotEqual(str(doc.sla_due), "2099-12-31")
		self.assertFalse(doc.assigned_to or doc.answer or doc.resolution)
		self.assertEqual(doc.raw_payload, "Wants to see her data", "what the person said is kept")
		self.assertEqual(doc.client_request_id, mid, "the SDK's mobile_uuid is the request ID")
		self.assertEqual(doc.raised_by_role, "by_field_worker")

	def test_a_retried_sdk_push_is_filed_once(self):
		frappe.set_user(WORKER)
		mid = str(uuid.uuid4())
		row = {"doctype": "Anumati Rights Request", "mobile_uuid": mid, "request_type": "erasure", "channel": "field_worker",
		       "matched_principal": self.p.name}
		client_insert(dict(row))
		self.assertRaises((frappe.UniqueValidationError, frappe.DuplicateEntryError), client_insert, dict(row))
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count("Anumati Rights Request", {"client_request_id": mid}), 1)

	def test_a_field_worker_cannot_set_a_grievance_outcome(self):
		frappe.set_user(WORKER)
		out = client_insert({
			"doctype": "Anumati Grievance", "category": "did_not_stop", "channel": "field_worker",
			"matched_principal": self.p.name, "description": "Calls continued after she said stop",
			"status": "request_closed", "outcome": "no_problem_found", "person_says": "solved",
			"answer": "Nothing wrong", "internal_note": "ignore", "dpo_since": "2020-01-01 00:00:00",
		})
		doc = frappe.get_doc("Anumati Grievance", out["name"])
		self.assertEqual(doc.status, "new_request")
		self.assertFalse(doc.outcome or doc.person_says or doc.answer or doc.internal_note or doc.dpo_since)
		self.assertEqual(doc.description, "Calls continued after she said stop")

	def test_staff_can_still_fill_in_staff_fields(self):
		frappe.set_user(OPERATOR)
		out = client_insert({
			"doctype": "Anumati Rights Request", "request_type": "access", "channel": "email",
			"matched_principal": self.p.name, "assigned_to": OPERATOR,
		})
		self.assertEqual(frappe.db.get_value("Anumati Rights Request", out["name"], "assigned_to"), OPERATOR)
