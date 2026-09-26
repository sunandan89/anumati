"""CI gate: role matrix (spec section 2) and unauthenticated access.

role_matrix.json is the reviewed matrix. If someone changes permissions in the DocType builder, this
test fails until the matrix file is updated in the same pull request."""

import importlib
import json
import os
import pkgutil

import frappe
from frappe.tests.utils import FrappeTestCase

import anumati

PTYPES = ("read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "import", "print", "email", "share")
# The only endpoints anyone may call without logging in. Adding one means adding it here, in review.
GUEST_ALLOWLIST = {"anumati.api.v1.consent.verify", "anumati.api.v1.consent.public_keys"}
TWO_FACTOR_ROLES = {"Anumati Admin", "Anumati DPO", "Anumati Operator", "Anumati Programme Manager"}


def expected_matrix():
	with open(os.path.join(os.path.dirname(__file__), "role_matrix.json")) as fh:
		return json.load(fh)


def anumati_doctypes():
	return frappe.get_all("DocType", {"module": "Anumati", "istable": 0}, pluck="name")


def import_app_modules():
	for mod in pkgutil.walk_packages(anumati.__path__, "anumati."):
		if ".tests" not in mod.name and not mod.name.endswith(".hooks"):
			importlib.import_module(mod.name)


def whitelisted(guest_only=False):
	import_app_modules()
	source = frappe.guest_methods if guest_only else frappe.whitelisted
	return {f"{fn.__module__}.{fn.__qualname__}" for fn in source if fn.__module__.startswith("anumati.")}


class TestRoleMatrix(FrappeTestCase):
	def test_every_doctype_is_in_the_matrix(self):
		self.assertEqual(set(anumati_doctypes()), set(expected_matrix()))

	def test_permissions_match_the_reviewed_matrix(self):
		for doctype, roles in expected_matrix().items():
			actual = {}
			for perm in frappe.get_meta(doctype).permissions:
				if perm.permlevel == 0:
					actual[perm.role] = sorted(p for p in PTYPES if perm.get(p))
			self.assertEqual(actual, roles, f"permissions drifted on {doctype}")

	def test_roles_exist_with_expected_desk_access_and_2fa(self):
		roles = {r for perms in expected_matrix().values() for r in perms} - {"System Manager"}
		for role in roles:
			self.assertTrue(frappe.db.exists("Role", role), role)
			self.assertEqual(bool(frappe.db.get_value("Role", role, "two_factor_auth")), role in TWO_FACTOR_ROLES, role)

	def test_field_worker_cannot_read_audit_or_governance(self):
		for doctype in ("Audit Entry", "ROPA Entry", "Breach Incident", "Channel Provider", "Anumati Settings"):
			roles = expected_matrix()[doctype]
			self.assertNotIn("Anumati Field Worker", roles, doctype)

	def test_auditor_and_funder_are_read_only(self):
		for doctype, roles in expected_matrix().items():
			for role in ("Anumati Auditor", "Anumati Funder Viewer", "Anumati Processor Partner"):
				self.assertTrue(set(roles.get(role, [])) <= {"read"}, f"{role} on {doctype}")


class TestGuestAccess(FrappeTestCase):
	def test_guest_cannot_read_any_anumati_doctype(self):
		for doctype in anumati_doctypes():
			for ptype in ("read", "write", "create", "delete"):
				self.assertFalse(frappe.has_permission(doctype, ptype, user="Guest"), f"Guest can {ptype} {doctype}")

	def test_guest_list_query_is_refused(self):
		frappe.set_user("Guest")
		try:
			for doctype in anumati_doctypes():
				self.assertRaises(frappe.PermissionError, frappe.get_list, doctype)
		finally:
			frappe.set_user("Administrator")

	def test_only_allowlisted_methods_are_open_to_guests(self):
		self.assertEqual(whitelisted(guest_only=True), GUEST_ALLOWLIST)

	def test_authenticated_methods_check_roles(self):
		frappe.set_user("Guest")
		try:
			from anumati.api.v1 import chain as chain_api

			self.assertRaises(frappe.PermissionError, chain_api.verify)
		finally:
			frappe.set_user("Administrator")
