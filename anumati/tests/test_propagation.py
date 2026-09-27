"""Processor and system routing, purge lifecycle, partner portal (Phase 2b, spec C7, C6, T15).
HTTP is mocked. Sample data is fictional."""

import hashlib
import hmac
import json
import uuid
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from anumati import propagation
from anumati.api.v1 import consent, processor, purge, rights
from anumati.tests.utils import make_principal, make_programme, make_purpose

PROG = "PRP"
SECRET = "dho-test-secret"


def user(email, role):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0,
		                "roles": [{"role": role}]}).insert(ignore_permissions=True)
	return email


def http(status=200):
	return patch("anumati.propagation.requests.post", return_value=MagicMock(status_code=status))


class TestPropagation(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_programme(PROG, "Propagation Test Programme")
		make_purpose(PROG, "screen", "Health screening", essential=1)
		make_purpose(PROG, "follow", "Follow-up calls")
		make_purpose(PROG, "research", "Research")
		make_purpose(PROG, "photos", "Photos and stories")
		cls.dho_user = user("dho-partner@example.org", "Anumati Processor Partner")
		cls.bank_user = user("bank-partner@example.org", "Anumati Processor Partner")
		cls.mis_user = user("mis-api@example.org", "Anumati Developer")
		cls.other_user = user("other-api@example.org", "Anumati Developer")
		for name, url, purposes, partner in (
			("District Health Office (test)", "https://dho.example.org/anumati", ["follow"], cls.dho_user),
			("Bank partner (test)", None, ["screen"], cls.bank_user),
		):
			if not frappe.db.exists("Processor", name):
				frappe.get_doc({"doctype": "Processor", "processor_name": name, "webhook_url": url, "webhook_secret": SECRET,
				                "partner_user": partner, "purposes": [{"purpose": f"{PROG}-{p}"} for p in purposes]}).insert()
		for name, api_user in (("MIS (test)", cls.mis_user), ("Other app (test)", cls.other_user)):
			if not frappe.db.exists("Source System", name):
				frappe.get_doc({"doctype": "Source System", "system_name": name, "system_type": "API",
				                "api_user": api_user, "enabled": 1}).insert()

	def tearDown(self):
		frappe.set_user("Administrator")

	def person(self, **kw):
		p = make_principal(full_name="Kavita R. (fictional)", phone="9000099001", **kw)
		consent.record({"event_uuid": str(uuid.uuid4()), "principal_ref": p.principal_ref, "programme": PROG,
		                "purposes_granted": ["screen", "follow", "research"], "channel": "app",
		                "device_time": "2026-09-20 11:20:00"})
		return p

	def used(self, system, principal, *codes):
		for c in codes:
			frappe.get_doc({"doctype": "System Usage Log", "source_system": system, "principal": principal.name,
			                "purpose": f"{PROG}-{c}", "checked_at": frappe.utils.now_datetime(), "result": "allow"}).insert()

	def acks(self, doctype, name):
		return frappe.get_all("Propagation Ack", {"reference_doctype": doctype, "reference_name": name},
		                      ["name", "processor", "source_system", "status"])

	def test_withdrawal_reaches_only_holders_of_that_purpose(self):
		p = self.person()
		self.used("MIS (test)", p, "follow")
		self.used("Other app (test)", p, "research")
		art = consent.withdraw_for(p.name, PROG, "sms", str(uuid.uuid4()), ["follow"])
		targets = {a.processor or a.source_system for a in self.acks("Consent Event", art["consent_id"])}
		self.assertEqual(targets, {"District Health Office (test)", "MIS (test)"})

	def test_delivery_is_signed_and_carries_no_personal_data(self):
		p = self.person()
		art = consent.withdraw_for(p.name, PROG, "sms", str(uuid.uuid4()), ["follow"])
		ack = [a for a in self.acks("Consent Event", art["consent_id"]) if a.processor][0]
		with http(200) as post:
			self.assertEqual(propagation.deliver(ack.name), "Sent")
		body, headers = post.call_args.kwargs["data"], post.call_args.kwargs["headers"]
		expected = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
		self.assertEqual(headers["X-Anumati-Signature"], expected)
		data = json.loads(body)
		self.assertEqual((data["event"], data["principal_ref"], data["purposes"]), ("consent.withdrawn", p.principal_ref, ["follow"]))
		self.assertNotIn("Kavita", body.decode())
		self.assertNotIn("9000099001", body.decode())

	def test_failed_delivery_backs_off_then_fails(self):
		p = self.person()
		art = consent.withdraw_for(p.name, PROG, "sms", str(uuid.uuid4()), ["follow"])
		ack = [a for a in self.acks("Consent Event", art["consent_id"]) if a.processor][0]
		with http(500):
			propagation.deliver(ack.name)
			doc = frappe.get_doc("Propagation Ack", ack.name)
			self.assertEqual((doc.status, doc.attempts), ("Pending", 1))
			self.assertTrue(doc.next_retry)
			for _ in range(propagation.MAX_ATTEMPTS):
				propagation.deliver(ack.name)
		self.assertEqual(frappe.db.get_value("Propagation Ack", ack.name, "status"), "Failed")

	def test_purge_list_and_ack_are_scoped_to_the_calling_system(self):
		p = self.person()
		self.used("MIS (test)", p, "screen", "follow", "research")
		req = frappe.get_doc({"doctype": "Rights Request", "request_type": "erasure", "channel": "slip",
		                      "matched_principal": p.name}).insert()
		out = rights.start_erasure(req.name)

		frappe.set_user(self.mis_user)
		listed = purge.list()["requests"]
		self.assertEqual({r["purposes"][0] for r in listed}, {"screen", "follow", "research"})
		self.assertNotIn("Kavita", json.dumps(listed))
		frappe.set_user(self.other_user)
		self.assertEqual(purge.list()["requests"], [])
		with self.assertRaises(frappe.DoesNotExistError):
			purge.ack(listed[0]["request_id"], "completed")

		frappe.set_user(self.mis_user)
		for r in listed:
			purge.ack(r["request_id"], "completed", evidence_hash="ab" * 32)
		frappe.set_user("Administrator")
		statuses = {frappe.db.get_value("Purge Request", n, "purpose"): frappe.db.get_value("Purge Request", n, "status")
		            for n in out["purge_requests"]}
		self.assertEqual(statuses[f"{PROG}-research"], "Completed")      # MIS was the only holder
		self.assertEqual(statuses[f"{PROG}-follow"], "Acknowledged")     # DHO hasn't confirmed yet
		self.assertEqual(statuses[f"{PROG}-screen"], "Acknowledged")     # bank hasn't confirmed yet

	def test_partner_sees_only_its_own_rows_and_must_give_proof(self):
		p = self.person()
		req = frappe.get_doc({"doctype": "Rights Request", "request_type": "erasure", "channel": "slip",
		                      "matched_principal": p.name}).insert()
		rights.start_erasure(req.name)
		frappe.set_user(self.dho_user)
		mine = processor.pending()["requests"]
		self.assertTrue(mine)
		self.assertTrue(all(r["purposes"] == ["follow"] for r in mine))
		with self.assertRaises(frappe.ValidationError):
			processor.confirm(mine[0]["request_id"])  # no proof
		self.assertEqual(processor.confirm(mine[0]["request_id"], deletion_reference="DHO-DEL-0042")["status"], "Completed")
		frappe.set_user(self.bank_user)
		with self.assertRaises(frappe.DoesNotExistError):
			processor.confirm(mine[0]["request_id"], evidence_hash="cd" * 32)
		self.assertTrue(all(r["purposes"] == ["screen"] for r in processor.pending()["requests"]))

	def test_purge_with_no_holder_needs_manual_action(self):
		p = self.person()
		pr = frappe.get_doc({"doctype": "Purge Request", "principal": p.name, "purpose": f"{PROG}-photos",
		                     "purge_action": "hard_purge", "status": "Requested", "due_on": frappe.utils.add_days(frappe.utils.today(), 30)}).insert()
		self.assertTrue(frappe.db.get_value("Purge Request", pr.name, "manual_action"))

	def test_host_system_fulfils_its_part_of_an_erasure(self):
		p = self.person()
		self.used("MIS (test)", p, "research")
		req = frappe.get_doc({"doctype": "Rights Request", "request_type": "erasure", "channel": "api",
		                      "matched_principal": p.name}).insert()
		out = rights.start_erasure(req.name)
		frappe.set_user(self.mis_user)
		self.assertEqual(rights.fulfil(req.name, "completed", evidence_hash="ef" * 32)["updated"], 1)
		frappe.set_user("Administrator")
		research = [n for n in out["purge_requests"] if frappe.db.get_value("Purge Request", n, "purpose") == f"{PROG}-research"][0]
		self.assertEqual(frappe.db.get_value("Purge Request", research, "status"), "Completed")
