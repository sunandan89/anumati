"""Evidence, v1: /api/v2/method/anumati.api.v1.evidence.view

Plays or shows one encrypted evidence file in the browser (audio, photo). Only staff who can read the
record it belongs to may open it; field workers can't read evidence back from the server. Every view
is written to the stock Access Log."""

import mimetypes
import os

import frappe
from frappe import _

from anumati import evidence

STAFF_ROLES = {"Anumati Admin", "Anumati DPO", "Anumati Operator", "Anumati Programme Manager", "System Manager"}


@frappe.whitelist(methods=["GET"])
def view(file_url):
	if not STAFF_ROLES & set(frappe.get_roles()):
		raise frappe.PermissionError
	name = frappe.db.get_value("File", {"file_url": file_url, "is_private": 1}, "name")
	if not name:
		frappe.throw(_("File not found"), frappe.DoesNotExistError)
	doc = frappe.get_doc("File", name)
	if not evidence.is_evidence(doc):
		raise frappe.PermissionError
	frappe.get_doc(doc.attached_to_doctype, doc.attached_to_name).check_permission("read")
	content = evidence.read_plain(doc)

	from frappe.core.doctype.access_log.access_log import make_access_log

	make_access_log(doctype=doc.attached_to_doctype, document=doc.attached_to_name,
	                file_type=os.path.splitext(doc.file_name or "")[1].lstrip(".") or "file")
	frappe.response.type = "download"
	frappe.response.filename = doc.file_name
	frappe.response.filecontent = content
	frappe.response.content_type = mimetypes.guess_type(doc.file_name or "")[0] or "application/octet-stream"
	frappe.response.display_content_as = "inline"
