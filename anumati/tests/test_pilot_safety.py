"""Pilot-safety fixes from the October 2026 review: the phone clock (C1), who sets the verification status
(C2), evidence checked against its file (C3), a chain clash is an error (C4), field devices bound to their
worker (C9) and idempotent requests (C10). Sample data is fictional."""

import uuid
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from anumati.api.v1 import consent, device, grievance, notifications, rights
from anumati.api.v1.consent import ConsentRequestError
from anumati.ledger import chain
from anumati.ledger.insert_only import InsertOnlyDocument
from anumati.tests.utils import make_evidence, make_principal, make_programme, make_purpose

PROG = "SAFE"


def uid():
	return str(uuid.uuid4())


def make_user(tag, role):
	email = f"safety.{tag}@example.com"
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": "Safety", "last_name": tag.title(),
		                "user_type": "System User", "send_welcome_email": 0, "roles": [{"role": role}]}).insert()
	return email


def field_worker(tag):
	return f"safety.{tag}@example.com"


class TestPilotSafety(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_programme(PROG, "Safety Test Programme")
		make_purpose(PROG, "screen", "Health screening", essential=1)
		make_purpose(PROG, "follow", "Follow-up calls")
		for tag in ("asha", "ravi"):
			make_user(tag, "Anumati Field Worker")
		make_user("desk", "Anumati Operator")
		make_user("coordinator", "Anumati Programme Manager")

	def setUp(self):
		frappe.set_user("Administrator")
		self.p = make_principal(phone="5550004400")

	def tearDown(self):
		frappe.set_user("Administrator")

	def grant(self, principal=None, **kw):
		principal = principal or self.p
		return consent.record({
			"event_uuid": kw.pop("event_uuid", uid()), "principal_ref": principal.principal_ref, "programme": PROG,
			"purposes_granted": ["screen", "follow"], "channel": "app", "device_id": "FW-SAFE-01",
			"capture_mode": "self_worker_device", **kw,
		})

	def status(self, code="follow", principal=None):
		return consent.check((principal or self.p).principal_ref, code, programme=PROG)["status"]

	# -- C1: the phone clock ---------------------------------------------------

	def test_a_phone_clock_ahead_cannot_outrank_a_later_withdrawal(self):
		# The grant's phone thinks it is next year; the person withdraws by SMS after it synced.
		ahead = add_to_date(now_datetime(), days=365).strftime("%Y-%m-%d %H:%M:%S")
		self.grant(device_time=ahead)
		consent.withdraw(self.p.principal_ref, PROG, channel="sms", event_uuid=uid(), purposes=["follow"])
		self.assertEqual(self.status(), "withdrawn")

	def test_an_offline_grant_that_syncs_late_still_loses_to_a_newer_withdrawal(self):
		consent.withdraw(self.p.principal_ref, PROG, channel="field_worker", event_uuid=uid(), purposes=["follow"],
		                 device_time=add_to_date(now_datetime(), days=-1).strftime("%Y-%m-%d %H:%M:%S"))
		self.grant(device_time=add_to_date(now_datetime(), days=-3).strftime("%Y-%m-%d %H:%M:%S"))
		self.assertEqual(self.status(), "withdrawn")

	# -- C2: only the server confirms --------------------------------------------

	def test_a_client_can_never_set_confirmed(self):
		for method in ("server_otp", "deferred", "device_sms_otp", "missed_call", "reverse_sms"):
			p = make_principal(phone="5550004401")
			kw = {"evidence": [make_evidence(p.name)]} if method == "device_sms_otp" else {}
			art = self.grant(p, verification_method=method, verification_status="confirmed", **kw)
			self.assertEqual(art["verification_status"], "recorded", method)

	def test_evidence_only_needs_evidence_that_checks_out(self):
		p = make_principal(no_phone=1)
		art = self.grant(p, verification_method="evidence_only", verification_status="evidence_only")
		self.assertEqual(art["verification_status"], "recorded", "no evidence: just recorded")
		q = make_principal(no_phone=1)
		art = self.grant(q, verification_method="evidence_only", evidence=[make_evidence(q.name, kind="thumbprint")])
		self.assertEqual(art["verification_status"], "evidence_only")

	# -- C3: evidence is the file it says -----------------------------------------

	def test_evidence_must_be_this_persons_file_with_the_signed_hash(self):
		other = make_principal()
		theirs = make_evidence(other.name)
		self.assertRaises(ConsentRequestError, self.grant, verification_method="evidence_only", evidence=[theirs])
		mine = make_evidence(self.p.name)
		self.assertRaises(ConsentRequestError, self.grant, verification_method="evidence_only",
		                  evidence=[{**mine, "sha256": "0" * 64}])
		self.assertRaises(ConsentRequestError, self.grant, verification_method="evidence_only",
		                  evidence=[{"file": "/private/files/no-such-file.m4a", "kind": "audio", "sha256": "0" * 64}])
		self.assertRaises(ConsentRequestError, self.grant, verification_method="evidence_only",
		                  evidence=[{"file": mine["file"], "kind": "audio"}])
		self.assertEqual(self.grant(verification_method="evidence_only", evidence=[mine])["verification_status"],
		                 "evidence_only")

	# -- C4: a chain clash is an error, never a silent "synced" ---------------------

	def test_a_chain_position_clash_raises_instead_of_returning_nothing(self):
		self.grant()
		head = frappe.db.get_value("Consent Event", {"chain_seq": (">", 0)}, "chain_seq", order_by="chain_seq desc")

		def clash(doc):
			chain.seal(doc)
			doc.chain_seq = head  # as if another writer took this position first

		event_uuid = uid()
		with patch.object(InsertOnlyDocument, "before_save", clash):
			self.assertRaises((frappe.DuplicateEntryError, frappe.UniqueValidationError), self.grant,
			                  event_uuid=event_uuid)
		self.assertFalse(frappe.db.exists("Consent Event", event_uuid))
		self.assertEqual(self.grant(event_uuid=event_uuid)["event_uuid"], event_uuid, "the retry goes through")

	def test_chain_lock_is_taken_when_sealing(self):
		with patch("anumati.ledger.chain.lock_chain", wraps=chain.lock_chain) as lock:
			self.grant()
		lock.assert_called_with("Consent Event")

	# -- C9: field devices ---------------------------------------------------------

	def test_only_field_workers_register_a_phone_and_it_stays_theirs(self):
		dev = f"DEV-{uuid.uuid4().hex[:6]}"
		frappe.set_user("safety.desk@example.com")
		self.assertRaises(frappe.PermissionError, device.register, dev)
		frappe.set_user(field_worker("asha"))
		self.assertEqual(device.register(dev)["status"], "active")
		frappe.set_user(field_worker("ravi"))
		self.assertRaises(device.DeviceTakenError, device.register, dev)
		frappe.set_user(field_worker("asha"))
		self.assertEqual(device.sign_out(dev)["status"], "logged_out")
		frappe.set_user(field_worker("ravi"))
		self.assertEqual(device.register(dev)["status"], "active", "after sign-out the next worker can sign in")
		self.assertEqual(frappe.db.get_value("Field Device", dev, "user"), field_worker("ravi"))

	def test_someone_else_cannot_use_up_a_lost_phones_wipe(self):
		dev = f"DEV-{uuid.uuid4().hex[:6]}"
		frappe.set_user(field_worker("asha"))
		device.register(dev)
		frappe.set_user("Administrator")
		device.report_lost(dev)
		frappe.set_user(field_worker("ravi"))
		self.assertRaises(device.DeviceTakenError, device.register, dev)
		self.assertEqual(frappe.db.get_value("Field Device", dev, "status"), "wipe_queued")
		frappe.set_user(field_worker("asha"))
		self.assertTrue(device.register(dev)["wipe"])

	# -- C10: a retried request is filed once ----------------------------------------

	def test_retried_rights_requests_and_grievances_are_filed_once(self):
		rid = uid()
		first = rights.submit("access", "field_worker", principal_ref=self.p.principal_ref, client_request_id=rid)
		again = rights.submit("access", "field_worker", principal_ref=self.p.principal_ref, client_request_id=rid)
		self.assertEqual(first["request"], again["request"])
		self.assertEqual(frappe.db.count("Rights Request", {"client_request_id": rid}), 1)

		gid = uid()
		first = rights.submit("grievance", "field_worker", principal_ref=self.p.principal_ref, payload="Calls continued",
		                      client_request_id=gid)
		again = rights.submit("grievance", "field_worker", principal_ref=self.p.principal_ref, payload="Calls continued",
		                      client_request_id=gid)
		self.assertEqual(first["request"], again["request"])
		self.assertEqual(frappe.db.count("Grievance", {"client_request_id": gid}), 1)

		hid = uid()
		one = grievance.submit("did_not_stop", "field_worker", principal_ref=self.p.principal_ref, client_request_id=hid)
		two = grievance.submit("did_not_stop", "field_worker", principal_ref=self.p.principal_ref, client_request_id=hid)
		self.assertEqual(one["grievance"], two["grievance"])

	def test_guardian_needed_tells_coordinators_once_per_request(self):
		rid = uid()
		before = frappe.db.count("Notification Log", {"document_name": PROG})
		told = notifications.guardian_needed(PROG, client_request_id=rid)["told"]
		self.assertGreaterEqual(told, 1, "the coordinator is told")
		self.assertEqual(notifications.guardian_needed(PROG, client_request_id=rid)["told"], told)
		self.assertEqual(frappe.db.count("Notification Log", {"document_name": PROG}) - before, told)

