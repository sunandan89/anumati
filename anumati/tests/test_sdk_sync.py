"""A Consent Event pushed by the Frappe Mobile SDK's standard sync: a plain frappe.client.insert by the field
worker, named by the phone's mobile_uuid, with evidence uploaded beforehand and not attached to anything.
The DocType itself applies every consent rule, so this path is as strict as consent.record.
Sample data is fictional."""

import hashlib
import uuid

import frappe
from frappe.client import insert as client_insert
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime, now_datetime

from anumati import evidence
from anumati.consent_rules import ConsentRequestError
from anumati.api.v1 import consent
from anumati.tests.utils import make_principal, make_programme, make_purpose

PROG = "SDK"
WORKER = "sdk.worker@example.com"
OTHER = "sdk.other@example.com"


def worker(email):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": "SDK", "last_name": "Worker",
		                "user_type": "System User", "send_welcome_email": 0,
		                "roles": [{"role": "Anumati Field Worker"}]}).insert()
	return email


class TestSdkSync(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_programme(PROG, "SDK Test Programme")
		make_purpose(PROG, "screen", "Health screening", essential=1)
		make_purpose(PROG, "follow", "Follow-up calls")
		make_purpose(PROG, "research", "Research", child_allowed=0)
		worker(WORKER)
		worker(OTHER)

	def setUp(self):
		frappe.set_user("Administrator")
		self.p = make_principal()
		frappe.set_user(WORKER)

	def tearDown(self):
		frappe.set_user("Administrator")

	def push(self, principal=None, **kw):
		"""What the SDK's PushEngine sends: the local row's columns, never `name`."""
		doc = {"doctype": "Consent Event", "mobile_uuid": kw.pop("mobile_uuid", str(uuid.uuid4())),
		       "principal": (principal or self.p).name, "programme": PROG, "action": "grant",
		       "purposes_granted": '["screen", "follow"]', "purposes_denied": "[]", "channel": "app",
		       "capture_mode": "self_worker_device", "verification_method": "deferred",
		       "device_time": "2026-10-10 10:00:00", **kw}
		return client_insert(doc)

	def upload(self, content, attach_to=None):
		f = frappe.get_doc({"doctype": "File", "file_name": f"{uuid.uuid4().hex[:8]}-clip.m4a", "content": content,
		                    "is_private": 1, **({"attached_to_doctype": "Data Principal", "attached_to_name": attach_to}
		                                        if attach_to else {})})
		f.insert(ignore_permissions=True)
		return {"file": f.file_url, "kind": "audio", "sha256": hashlib.sha256(content).hexdigest()}

	def test_an_sdk_insert_is_named_by_its_mobile_uuid_and_sealed_by_the_server(self):
		mid = str(uuid.uuid4())
		out = self.push(mobile_uuid=mid, verification_status="confirmed", server_time="2020-01-01 00:00:00",
		                chain_seq=1, hash="f" * 64, signature="forged", captured_by=OTHER)
		self.assertEqual(out["name"], mid)
		doc = frappe.get_doc("Consent Event", mid)
		self.assertEqual(doc.event_uuid, mid)
		self.assertEqual(doc.verification_status, "recorded", "the phone can't confirm its own consent")
		self.assertEqual(doc.captured_by, WORKER)
		self.assertGreater(get_datetime(doc.server_time), get_datetime("2026-01-01"), "server time is the server's")
		self.assertLessEqual(get_datetime(doc.server_time), now_datetime())
		self.assertNotEqual(doc.signature, "forged")
		frappe.set_user("Administrator")
		self.assertTrue(consent.verify(doc.hash)["signature_valid"])
		self.assertEqual(doc.short_code, consent.short_code(mid), "the receipt code the phone printed offline")

	def test_a_retried_push_does_not_make_a_second_event(self):
		mid = str(uuid.uuid4())
		self.push(mobile_uuid=mid)
		self.assertRaises((frappe.DuplicateEntryError, frappe.UniqueValidationError), self.push, mobile_uuid=mid)
		self.assertEqual(frappe.db.count("Consent Event", {"event_uuid": mid}), 1)

	def test_the_consent_rules_apply_to_an_sdk_insert(self):
		frappe.set_user("Administrator")
		child = make_principal(is_minor=1)
		frappe.set_user(WORKER)
		self.assertRaises(ConsentRequestError, self.push, child)
		self.assertRaises(ConsentRequestError, self.push, purposes_granted='["nope"]')
		self.assertRaises(ConsentRequestError, self.push, verification_method="device_sms_otp")
		self.assertRaises(ConsentRequestError, self.push, action="delete_everything")

	def test_evidence_uploaded_by_the_sdk_is_checked_attached_and_encrypted(self):
		content = f"fictional haan {uuid.uuid4().hex}".encode() * 10
		entry = self.upload(content)
		out = self.push(verification_method="evidence_only", evidence=[entry])
		self.assertEqual(frappe.db.get_value("Consent Event", out["name"], "verification_status"), "evidence_only")
		frappe.set_user("Administrator")
		name = frappe.db.get_value("File", {"file_url": entry["file"], "attached_to_name": self.p.name})
		self.assertTrue(name, "the upload now belongs to the person")
		f = frappe.get_doc("File", name)
		with open(f.get_full_path(), "rb") as fh:
			self.assertTrue(fh.read().startswith(evidence.MAGIC), "encrypted on disk")
		self.assertEqual(evidence.read_plain(f), content)

	def test_someone_elses_unattached_upload_is_not_evidence(self):
		frappe.set_user(OTHER)
		entry = self.upload(f"fictional other {uuid.uuid4().hex}".encode() * 10)
		frappe.set_user(WORKER)
		self.assertRaises(ConsentRequestError, self.push, verification_method="evidence_only", evidence=[entry])

	def test_a_withdrawal_can_be_pushed_too(self):
		self.push()
		self.push(action="withdraw", purposes_granted="[]", purposes_denied='["follow"]',
		          device_time="2026-10-11 10:00:00")
		frappe.set_user("Administrator")
		state = frappe.db.get_value("Consent State", f"{self.p.name}-{PROG}-follow", "status")
		self.assertEqual(state, "withdrawn")
