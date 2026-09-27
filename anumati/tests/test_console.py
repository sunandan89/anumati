"""Console core (Phase 1f): the stock Workspace, number cards and chart ship with the app."""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestConsole(FrappeTestCase):
	def test_workspace_cards_and_chart_are_installed(self):
		self.assertTrue(frappe.db.exists("Workspace", "Anumati"))
		for card in ("Consents This Week", "Withdrawals This Week", "Open Rights Requests", "Unmatched Requests"):
			self.assertTrue(frappe.db.exists("Number Card", card), card)
		self.assertTrue(frappe.db.exists("Dashboard Chart", "Consent Events Per Week"))

	def test_number_cards_compute(self):
		from frappe.desk.doctype.number_card.number_card import get_result

		for card in ("Open Rights Requests", "Consents This Week"):
			doc = frappe.get_doc("Number Card", card)
			self.assertIsInstance(get_result(doc.as_dict(), doc.filters_json), int | float)
