"""Evidence files encrypted at rest (CLAUDE.md non-negotiable: field-level encryption for evidence).

Voice clips, thumbprint photos and guardian documents arrive through Frappe's stock upload as private
files attached to a Data Principal (or Guardian Link). Right after the File is created, its bytes on
disk are replaced by a Fernet token made with the site's own encryption key, the same key Frappe
uses for Password fields. The consent ledger signs the SHA-256 of the original bytes, so a decrypted
file can still be checked against the signed record.

Staff play or view evidence through anumati.api.v1.evidence.view, which checks permission, decrypts
in memory and writes a stock Access Log entry. Downloading the raw file only ever yields ciphertext."""

import hashlib
import os

import frappe
from cryptography.fernet import Fernet
from frappe.utils.password import get_encryption_key

MAGIC = b"ANUMATI-ENC1\n"
EVIDENCE_DOCTYPES = ("Data Principal", "Guardian Link", "Consent Event")


def _fernet() -> Fernet:
	return Fernet(get_encryption_key().encode())


def _path(file_doc) -> str | None:
	if not file_doc.file_url or file_doc.is_folder:
		return None
	try:
		path = file_doc.get_full_path()
	except Exception:
		return None
	return path if path and os.path.isfile(path) else None


def is_evidence(file_doc) -> bool:
	return bool(file_doc.is_private) and file_doc.attached_to_doctype in EVIDENCE_DOCTYPES


def encrypt_file(doc, method=None):
	"""File after_insert: encrypt evidence on disk. Idempotent (encrypted files start with MAGIC)."""
	if not is_evidence(doc):
		return
	path = _path(doc)
	if not path:
		return
	with open(path, "rb") as fh:
		data = fh.read()
	if data.startswith(MAGIC):
		return
	token = _fernet().encrypt(data)
	tmp = path + ".anumati-tmp"
	with open(tmp, "wb") as fh:
		fh.write(MAGIC + token)
	os.replace(tmp, path)


def read_plain(file_doc) -> bytes:
	"""The original bytes of an evidence file (decrypts; plain files from before encryption pass through)."""
	path = _path(file_doc)
	if not path:
		raise frappe.DoesNotExistError
	with open(path, "rb") as fh:
		data = fh.read()
	if data.startswith(MAGIC):
		return _fernet().decrypt(data[len(MAGIC):])
	return data


def sha256_of(file_doc) -> str:
	return hashlib.sha256(read_plain(file_doc)).hexdigest()


def encrypt_existing():
	"""after_migrate: encrypt evidence uploaded before this feature existed. Safe to re-run."""
	for name in frappe.get_all("File", {"is_private": 1, "attached_to_doctype": ("in", EVIDENCE_DOCTYPES),
	                                     "is_folder": 0}, pluck="name"):
		try:
			encrypt_file(frappe.get_doc("File", name))
		except Exception:
			frappe.log_error(title="Anumati: could not encrypt an evidence file")
