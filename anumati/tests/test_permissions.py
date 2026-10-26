"""CI gate: role matrix (spec section 2) and unauthenticated access.

role_matrix.json is the reviewed matrix. If someone changes permissions in the DocType builder, this
test fails until the matrix file is updated in the same pull request."""

import importlib
import json
import os
import pkgutil

import frappe
from frappe.tests import IntegrationTestCase

import anumati

PTYPES = ("read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "import", "print", "email", "share")
# The only endpoints anyone may call without logging in. Adding one means adding it here, in review.
GUEST_ALLOWLIST = {
	"anumati.api.v1.consent.verify",
	"anumati.api.v1.consent.public_keys",
	# SMS gateway callbacks: each call must carry the Channel Provider inbound secret
	"anumati.api.v1.channel.inbound_sms",
	"anumati.api.v1.channel.missed_call",
	"anumati.api.v1.channel.delivery_report",
	# Self-service page (/my-consent). Signing in: an SMS code to a number we hold, or a receipt code and year
	# of birth; rate-limited, with tries counted per number and per code.
	"anumati.selfservice.start",
	"anumati.selfservice.verify",
	"anumati.selfservice.code_login",
	"anumati.selfservice.home",
	"anumati.selfservice.sign_out",
	"anumati.selfservice.choose",
	# Signed in only: each one needs the page's session cookie and answers 401 without it.
	"anumati.selfservice.overview",
	"anumati.selfservice.save_choices",
	"anumati.selfservice.leave",
	"anumati.selfservice.receipt",
	"anumati.selfservice.ask",
	"anumati.selfservice.write",
	"anumati.selfservice.complain",
	"anumati.selfservice.respond",
}
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


class TestRoleMatrix(IntegrationTestCase):
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
		for doctype in ("Anumati Audit Entry", "Anumati ROPA Entry", "Anumati Breach Incident", "Anumati Channel Provider", "Anumati Settings"):
			roles = expected_matrix()[doctype]
			self.assertNotIn("Anumati Field Worker", roles, doctype)

	def test_auditor_and_funder_are_read_only(self):
		for doctype, roles in expected_matrix().items():
			for role in ("Anumati Auditor", "Anumati Funder Viewer", "Anumati Processor Partner"):
				self.assertTrue(set(roles.get(role, [])) <= {"read"}, f"{role} on {doctype}")


class TestGuestAccess(IntegrationTestCase):
	def test_guest_cannot_read_any_anumati_doctype(self):
		for doctype in anumati_doctypes():
			for ptype in ("read", "write", "create", "delete"):
				self.assertFalse(frappe.has_permission(doctype, ptype, user="Guest"), f"Guest can {ptype} {doctype}")

	def test_guest_list_query_is_refused(self):
		frappe.set_user("Guest")
		try:
			from frappe.client import get as client_get

			for doctype in anumati_doctypes():
				if frappe.get_meta(doctype).issingle:
					# Single records (Anumati Settings) have no list; a guest reads them through frappe.client.get.
					self.assertRaises(frappe.PermissionError, client_get, doctype)
				else:
					self.assertRaises(frappe.PermissionError, frappe.get_list, doctype)
		finally:
			frappe.set_user("Administrator")

	def test_only_allowlisted_methods_are_open_to_guests(self):
		self.assertEqual(whitelisted(guest_only=True), GUEST_ALLOWLIST)

	def test_authenticated_methods_check_roles(self):
		from anumati.api.v1 import chain as chain_api

		# frappe.only_for is a no-op while frappe.flags.in_test is set; switch it off for this check.
		in_test = frappe.flags.in_test
		frappe.flags.in_test = False
		frappe.set_user("Guest")
		try:
			self.assertRaises(frappe.PermissionError, chain_api.verify)
		finally:
			frappe.set_user("Administrator")
			frappe.flags.in_test = in_test


class TestFormConnections(IntegrationTestCase):
	def test_forms_show_related_records(self):
		expect = {
			"Anumati Programme": {"Anumati Purpose", "Anumati Notice Template", "Anumati Consent Event"},
			"Anumati Notice Template": {"Anumati Notice Translation", "Anumati Consent Event"},
			"Anumati Data Principal": {"Anumati Consent Event", "Anumati Consent State", "Anumati Guardian Link", "Anumati Rights Request"},
		}
		for doctype, linked in expect.items():
			got = {link.link_doctype for link in frappe.get_meta(doctype).links}
			self.assertTrue(linked <= got, f"{doctype} connections missing {linked - got}")


class TestApiTypes(IntegrationTestCase):
	def test_every_whitelisted_method_is_type_annotated(self):
		"""Frappe v16 checks request arguments against these hints, so every parameter carries one."""
		import inspect

		import_app_modules()
		for fn in frappe.whitelisted:
			if not fn.__module__.startswith("anumati."):
				continue
			params = inspect.signature(fn).parameters.items()
			missing = [n for n, p in params if n not in ("self", "cls") and p.annotation is inspect.Parameter.empty]
			self.assertFalse(missing, f"{fn.__module__}.{fn.__qualname__}: {missing}")
