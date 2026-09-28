"""Desk console: role-based stock Workspaces, cards, charts, Requests board, saved filters, onboarding.

workspace_roles.json (written by tools/gen_desk.py) is the reviewed table of who sees which section.
The sidebar test logs in as a user holding one role and checks the stock sidebar shows exactly that."""

import json
import os

import frappe
from frappe.tests.utils import FrappeTestCase

HERE = os.path.dirname(__file__)
OPTIONAL_DOCTYPES = {"Mobile Configuration"}  # from the Frappe Mobile Control app, absent in CI


def expected_sections():
	with open(os.path.join(HERE, "workspace_roles.json")) as fh:
		return json.load(fh)


def user_with_role(role):
	email = f"console.{frappe.scrub(role)}@example.com"
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": "Console", "last_name": "Test",
						"user_type": "System User", "send_welcome_email": 0, "roles": [{"role": role}]}).insert()
	return email


class TestConsole(FrappeTestCase):
	def test_workspaces_have_the_reviewed_roles(self):
		self.assertFalse(frappe.db.exists("Workspace", "Anumati"), "old single workspace should be removed")
		for name, roles in expected_sections().items():
			ws = frappe.get_doc("Workspace", name)
			self.assertEqual({r.role for r in ws.roles}, set(roles), name)
			self.assertEqual(ws.module, "Anumati")

	def test_each_role_sees_only_its_sections(self):
		from frappe.desk.desktop import get_workspace_sidebar_items

		sections = expected_sections()
		roles = {r for rs in sections.values() for r in rs if r != "System Manager"} | {"Anumati Field Worker"}
		for role in roles:
			frappe.set_user(user_with_role(role))
			try:
				pages = {p["name"] for p in get_workspace_sidebar_items()["pages"]}
			finally:
				frappe.set_user("Administrator")
			want = {name for name, rs in sections.items() if role in rs}
			self.assertEqual(pages & set(sections), want, role)

	def test_workspace_widgets_exist_and_links_resolve(self):
		for name in expected_sections():
			ws = frappe.get_doc("Workspace", name)
			for card in ws.number_cards:
				self.assertTrue(frappe.db.exists("Number Card", card.number_card_name), card.number_card_name)
			for chart in ws.charts:
				self.assertTrue(frappe.db.exists("Dashboard Chart", chart.chart_name), chart.chart_name)
			for block in ws.custom_blocks:
				self.assertTrue(frappe.db.exists("Custom HTML Block", block.custom_block_name))
			for link in ws.links:
				if link.type == "Link" and link.link_to not in OPTIONAL_DOCTYPES:
					self.assertTrue(frappe.db.exists("DocType", link.link_to), f"{name}: {link.link_to}")
			for sc in ws.shortcuts:
				if sc.type == "DocType":
					self.assertTrue(frappe.db.exists("DocType", sc.link_to), f"{name}: {sc.link_to}")
			content = json.loads(ws.content)
			self.assertTrue(content, name)

	def test_number_cards_compute(self):
		from frappe.desk.doctype.number_card.number_card import get_result

		for name in frappe.get_all("Number Card", filters={"module": "Anumati"}, pluck="name"):
			doc = frappe.get_doc("Number Card", name)
			self.assertIsInstance(get_result(doc.as_dict(), doc.filters_json), int | float, name)

	def test_charts_compute(self):
		from frappe.desk.doctype.dashboard_chart.dashboard_chart import get

		for name in frappe.get_all("Dashboard Chart", filters={"module": "Anumati"}, pluck="name"):
			data = get(chart_name=name, refresh=1)
			self.assertIn("labels", data, name)

	def test_requests_board_covers_every_status(self):
		board = frappe.get_doc("Kanban Board", "Requests")
		self.assertEqual(board.reference_doctype, "Rights Request")
		self.assertFalse(board.private)
		options = frappe.get_meta("Rights Request").get_field("status").options.split("\n")
		self.assertEqual([c.column_name for c in board.columns], options)
		for field in json.loads(board.fields):
			self.assertTrue(frappe.get_meta("Rights Request").has_field(field), field)

	def test_saved_filters_are_shared_and_valid(self):
		rows = frappe.get_all("List Filter", filters={"name": ["like", "anumati-%"]}, fields=["*"])
		self.assertGreaterEqual(len(rows), 10)
		for row in rows:
			self.assertFalse(row.for_user, row.filter_name)
			meta = frappe.get_meta(row.reference_doctype)
			for f in json.loads(row.filters):
				self.assertTrue(meta.has_field(f[1]) or f[1] in ("creation", "modified"), f"{row.filter_name}: {f[1]}")

	def test_needs_attention_block_is_public(self):
		block = frappe.get_doc("Custom HTML Block", "Needs Attention")
		self.assertFalse(block.private)
		self.assertIn("frappe.model.can_read", block.script)

	def test_onboarding_is_for_admins_and_steps_resolve(self):
		ob = frappe.get_doc("Module Onboarding", "Anumati")
		self.assertEqual({r.role for r in ob.allow_roles}, {"Anumati Admin", "System Manager"})
		self.assertEqual(len(ob.steps), 6)
		for row in ob.steps:
			step = frappe.get_doc("Onboarding Step", row.step)
			self.assertTrue(frappe.db.exists("DocType", step.reference_document), step.title)

	def test_dpo_can_read_access_logs(self):
		for doctype in ("Access Log", "View Log"):
			self.assertTrue(frappe.has_permission(doctype, "read", user=user_with_role("Anumati DPO")), doctype)
			self.assertFalse(frappe.has_permission(doctype, "read", user=user_with_role("Anumati Operator")), doctype)
			self.assertFalse(frappe.has_permission(doctype, "write", user=user_with_role("Anumati DPO")), doctype)

	def test_forms_open_on_a_tab(self):
		for doctype in ("Programme", "Notice Template", "Data Principal", "Consent Event", "Rights Request", "Breach Incident"):
			self.assertEqual(frappe.get_meta(doctype).fields[0].fieldtype, "Tab Break", doctype)
		# Signature, hash and chain stay on the Consent Event form, in their own "Proof" tab.
		fields = [f.fieldname for f in frappe.get_meta("Consent Event").fields]
		self.assertLess(fields.index("proof_tab"), fields.index("hash"))
