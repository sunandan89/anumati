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
EVIDENCE_DOCTYPES = ("Data Principal", "Guardian Link", "Consent Event", "Grievance")


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


class EvidenceError(frappe.ValidationError):
	pass


def check_event_evidence(principal: str, entries, guardian_link: str | None = None) -> int:
	"""Every evidence entry on a consent event must be an uploaded private file of this person (or their
	guardian link) whose bytes hash to the sha256 the event signs (review C3). The Frappe Mobile SDK uploads
	files before the record and without attaching them, so a private file that is not attached to anything
	yet counts when the same user uploaded it; adopt_uploads then attaches and encrypts it. Returns how many
	entries were checked; raises EvidenceError on the first that fails. Messages name the entry, never a value."""
	owners = {("Data Principal", principal)}
	if guardian_link:
		owners.add(("Guardian Link", guardian_link))
	for i, entry in enumerate(entries or [], start=1):
		url, digest = (entry or {}).get("file"), ((entry or {}).get("sha256") or "").lower()
		if not url or not digest:
			frappe.throw(frappe._("Evidence {0} needs both its file and its sha256").format(i), EvidenceError)
		files = frappe.get_all("File", {"file_url": url, "is_private": 1, "is_folder": 0},
		                       ["name", "attached_to_doctype", "attached_to_name", "owner"])
		match = next((f for f in files if (f.attached_to_doctype, f.attached_to_name) in owners), None) or next(
			(f for f in files if not f.attached_to_doctype and f.owner == frappe.session.user), None)
		if not match:
			frappe.throw(frappe._("Evidence {0} is not a file uploaded for this person").format(i), EvidenceError)
		if sha256_of(frappe.get_doc("File", match.name)) != digest:
			frappe.throw(frappe._("Evidence {0} does not match its sha256").format(i), EvidenceError)
	return len(entries or [])


def guardian_link_has_evidence(guardian_link: str | None, principal: str) -> bool:
	"""The guardian's order or ID photo, uploaded for this person, counts as evidence for evidence_only."""
	if not guardian_link:
		return False
	urls = [u for u in frappe.db.get_value("Guardian Link", guardian_link, ["evidence", "id_document"]) or () if u]
	return bool(urls) and bool(frappe.db.exists("File", {
		"file_url": ("in", urls), "is_private": 1,
		"attached_to_doctype": ("in", ["Data Principal", "Guardian Link"]),
		"attached_to_name": ("in", [principal, guardian_link])}))


def adopt_uploads(principal: str, entries, uploader: str):
	"""After a consent event is saved: evidence the SDK uploaded unattached is attached to the person and
	encrypted on disk, like evidence uploaded the older way."""
	for entry in entries or []:
		url = (entry or {}).get("file")
		if not url:
			continue
		for name in frappe.get_all("File", {"file_url": url, "is_private": 1, "is_folder": 0, "owner": uploader,
		                                     "attached_to_doctype": ("is", "not set")}, pluck="name"):
			frappe.db.set_value("File", name, {"attached_to_doctype": "Data Principal", "attached_to_name": principal})
			encrypt_file(frappe.get_doc("File", name))
