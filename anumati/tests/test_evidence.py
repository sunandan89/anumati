"""Evidence encrypted at rest; staff can still play or view it (logged); Desk shows the name and a masked
phone only. Sample data is fictional."""

import hashlib
import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from anumati import demo, evidence
from anumati.api.v1 import evidence as evidence_api
from anumati.api.v1 import principal as principal_api
from anumati.tests.utils import make_principal

CLIP = b"fictional voice clip bytes " * 40


class TestEvidenceAtRest(FrappeTestCase):
	def upload(self, p, content=CLIP, name="clip.m4a"):
		return frappe.get_doc({
			"doctype": "File", "file_name": f"{uuid.uuid4().hex[:6]}-{name}", "content": content, "is_private": 1,
			"attached_to_doctype": "Data Principal", "attached_to_name": p.name,
		}).insert(ignore_permissions=True)

	def test_uploaded_evidence_is_encrypted_on_disk_and_decrypts_to_the_signed_hash(self):
		p = make_principal()
		f = self.upload(p)
		with open(f.get_full_path(), "rb") as fh:
			on_disk = fh.read()
		self.assertTrue(on_disk.startswith(evidence.MAGIC))
		self.assertNotIn(b"fictional voice clip", on_disk)
		self.assertEqual(evidence.read_plain(f), CLIP)
		self.assertEqual(evidence.sha256_of(f), hashlib.sha256(CLIP).hexdigest())
		evidence.encrypt_file(f)  # idempotent
		self.assertEqual(evidence.read_plain(f), CLIP)

	def test_staff_can_play_it_and_each_view_is_logged(self):
		p = make_principal()
		f = self.upload(p)
		before = frappe.db.count("Access Log", {"reference_document": p.name})
		evidence_api.view(f.file_url)
		self.assertEqual(frappe.response.filecontent, CLIP)
		self.assertEqual(frappe.response.display_content_as, "inline")
		self.assertEqual(frappe.db.count("Access Log", {"reference_document": p.name}), before + 1)

	def test_field_workers_cannot_read_evidence_back(self):
		p = make_principal()
		f = self.upload(p)
		demo.create_field_worker("Ev@test-2026")
		frappe.set_user(demo.FIELD_WORKER)
		try:
			self.assertRaises(frappe.PermissionError, evidence_api.view, f.file_url)
		finally:
			frappe.set_user("Administrator")

	def test_other_private_files_are_left_alone(self):
		f = frappe.get_doc({"doctype": "File", "file_name": f"{uuid.uuid4().hex[:6]}-note.txt", "content": b"plain note",
		                    "is_private": 1}).insert(ignore_permissions=True)
		with open(f.get_full_path(), "rb") as fh:
			self.assertEqual(fh.read(), b"plain note")


class TestMaskedPhone(FrappeTestCase):
	def test_mask_hides_the_last_three_digits(self):
		self.assertEqual(principal_api.mask_phone("9876543210"), "9876543XXX")
		self.assertEqual(principal_api.mask_phone("+91 98765 43210"), "919876543XXX")
		self.assertEqual(principal_api.mask_phone(""), "")

	def test_reveal_shows_name_and_masked_phone_only(self):
		p = make_principal(full_name="Kamla D. (fictional)", phone="5550001234")
		out = principal_api.reveal(p.name)
		self.assertEqual(out["full_name"], "Kamla D. (fictional)")
		self.assertEqual(out["phone_masked"], "5550001XXX")
		self.assertNotIn("5550001234", str(out))
