"""Which notices a field worker's phone may download.

The Frappe Mobile SDK pulls notices with ordinary list reads, so the rule lives here rather than in
notice.get_active: a field worker sees only published notices for their own programmes, and only the
translations of those notices. Staff see every notice, drafts and retired versions included.

"Their own programmes" are their User Permissions on Programme. Frappe applies those to Notice
Template itself (it links to Programme); a Notice Translation links only to its notice, so the
programme check is spelled out for it here."""

import frappe
from frappe.permissions import get_user_permissions

from anumati.intake import STAFF_ROLES


def _sees_everything(user) -> bool:
	return user == "Administrator" or bool(STAFF_ROLES & set(frappe.get_roles(user)))


def _programmes(user):
	"""Programmes the user is limited to, or None when they are not limited."""
	rows = get_user_permissions(user).get("Anumati Programme")
	return [r.get("doc") for r in rows] if rows else None


def _published(user) -> str:
	sql = "`tabAnumati Notice Template`.`docstatus` = 1 and `tabAnumati Notice Template`.`status` = 'Published'"
	programmes = _programmes(user)
	if programmes is not None:
		sql += " and `tabAnumati Notice Template`.`programme` in ({})".format(", ".join(frappe.db.escape(p) for p in programmes))
	return sql


def notice_conditions(user=None):
	user = user or frappe.session.user
	return "" if _sees_everything(user) else _published(user)


def translation_conditions(user=None):
	user = user or frappe.session.user
	if _sees_everything(user):
		return ""
	return f"`tabAnumati Notice Translation`.`notice` in (select `tabAnumati Notice Template`.`name` from `tabAnumati Notice Template` where {_published(user)})"


def notice_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _sees_everything(user) or ptype not in (None, "read", "select", "print", "export"):
		return True
	programmes = _programmes(user)
	return bool(doc.docstatus == 1 and doc.status == "Published" and (programmes is None or doc.programme in programmes))


def translation_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _sees_everything(user) or ptype not in (None, "read", "select", "print", "export"):
		return True
	notice = frappe.db.get_value("Anumati Notice Template", doc.notice, ["docstatus", "status", "programme"], as_dict=True)
	programmes = _programmes(user)
	return bool(notice and notice.docstatus == 1 and notice.status == "Published"
	            and (programmes is None or notice.programme in programmes))
