"""One-click field app setup: demo programme with a published notice and reviewed Hindi translation, a test
field worker, and Mobile Control switched on when installed. All data is fictional."""

import frappe
from frappe.tests.utils import FrappeTestCase

from anumati import demo
from anumati.api.v1 import notice


class TestFieldAppSetup(FrappeTestCase):
	def test_setup_is_idempotent_and_serves_a_reviewed_hindi_notice(self):
		first = demo.setup_field_app()
		second = demo.setup_field_app()
		self.assertEqual(first["notice"], second["notice"])
		self.assertEqual(frappe.db.count("Notice Template", {"programme": demo.PROGRAMME}), 1)
		out = notice.get_active(demo.PROGRAMME, language="hi")
		self.assertEqual({p["code"] for p in out["purposes"]}, {"screen", "follow", "photos", "research"})
		self.assertIsNotNone(out["translation"], "the demo Hindi translation is reviewed, so it is served")
		self.assertEqual(out["translation"]["label_yes_all"], "सब के लिए हाँ")

	def test_three_realistic_programmes_each_with_a_published_hindi_notice(self):
		demo.create_demo_programme()
		for spec in demo.PROGRAMMES:
			self.assertEqual(frappe.db.get_value("Programme", spec["code"], "programme_name"), spec["name"])
			out = notice.get_active(spec["code"], language="hi")
			self.assertEqual(len(out["purposes"]), 4, spec["code"])
			self.assertIsNotNone(out["translation"], spec["code"])
		self.assertEqual(frappe.db.get_value("Programme", "DEMO", "programme_name"), "Village Health Camps")

	def test_old_demo_name_is_renamed(self):
		demo.create_demo_programme()
		frappe.db.set_value("Programme", "DEMO", "programme_name", "Demo Health Camp (fictional)")
		demo.create_demo_programme()
		self.assertEqual(frappe.db.get_value("Programme", "DEMO", "programme_name"), "Village Health Camps")
		name = frappe.db.get_value("Notice Template", {"programme": "DEMO"}, "name")
		self.assertEqual(frappe.db.get_value("Notice Template", name, "programme_name"), "Village Health Camps")

	def test_field_worker_gets_roles_and_a_fresh_password(self):
		p1 = demo.create_field_worker()
		p2 = demo.create_field_worker()
		self.assertNotEqual(p1, p2)
		roles = frappe.get_roles(demo.FIELD_WORKER)
		self.assertIn("Anumati Field Worker", roles)
		self.assertNotIn("System Manager", roles)
		from frappe.utils.password import check_password

		self.assertEqual(check_password(demo.FIELD_WORKER, p2), demo.FIELD_WORKER)

	def test_site_config_password_sets_up_demo_on_migrate(self):
		from frappe.utils.password import check_password

		frappe.conf.anumati_demo_password = "Demo@test-2026"
		try:
			demo.after_migrate()
		finally:
			frappe.conf.pop("anumati_demo_password", None)
		self.assertEqual(check_password(demo.FIELD_WORKER, "Demo@test-2026"), demo.FIELD_WORKER)
		self.assertTrue(frappe.db.exists("Notice Template", {"programme": demo.PROGRAMME, "status": "Published"}))

	def test_mobile_configuration_is_switched_on_when_mobile_control_is_installed(self):
		installed = frappe.db.exists("DocType", "Mobile Configuration")
		self.assertEqual(demo.configure_mobile_app(), bool(installed))
		if installed:
			config = frappe.get_single("Mobile Configuration")
			self.assertTrue(config.enabled)
			self.assertEqual(config.package_name, demo.PACKAGE)

	def test_sample_data_is_fictional_signed_and_captured_by_the_field_worker(self):
		first = demo.create_sample_data()
		again = demo.create_sample_data()
		self.assertEqual(again["people"], 0, "idempotent")
		refs = [f"{demo.PROGRAMME}-{p[0]}" for p in demo.SAMPLE_PEOPLE]
		self.assertEqual(frappe.db.count("Data Principal", {"principal_ref": ("in", refs)}), len(refs))
		events = frappe.get_all("Consent Event", {"programme": demo.PROGRAMME, "captured_by": demo.FIELD_WORKER},
		                        ["hash", "signature", "action"])
		self.assertGreaterEqual(len(events), len(refs))
		self.assertTrue(all(e.hash and e.signature for e in events))
		self.assertIn("withdraw", {e.action for e in events})
		self.assertEqual(frappe.session.user, "Administrator", "the admin session is restored")
		for ref in refs:
			doc = frappe.get_doc("Data Principal", {"principal_ref": ref})
			phone = doc.get_password("phone", raise_exception=False)
			self.assertTrue(not phone or phone.startswith("555"), "sample numbers can never be real mobiles")
		self.assertGreaterEqual(first["consents"] + again["consents"], 0)

	def test_only_system_managers_can_run_it(self):
		in_test = frappe.flags.in_test
		frappe.flags.in_test = False  # frappe.only_for is a no-op in tests
		frappe.set_user("Guest")
		try:
			self.assertRaises(frappe.PermissionError, demo.setup_field_app)
			self.assertRaises(frappe.PermissionError, demo.add_sample_data)
		finally:
			frappe.set_user("Administrator")
			frappe.flags.in_test = in_test
