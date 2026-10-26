"""Install hygiene: installing or migrating Anumati inside a client's site changes nothing outside Anumati's
own records unless an admin asks for it, and uninstalling removes what Anumati added to stock DocTypes."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from anumati import demo, hooks, install
from anumati.anumati.report.who_opened_personal_records import who_opened_personal_records as report
from anumati.tests.test_console import user_with_role


class TestInstall(FrappeTestCase):
	def test_install_leaves_two_factor_sign_in_to_the_admin(self):
		frappe.db.set_single_value("System Settings", "enable_two_factor_auth", 0)
		install.after_install()
		install.after_migrate()
		self.assertFalse(frappe.db.get_single_value("System Settings", "enable_two_factor_auth"))

	def test_settings_box_switches_two_factor_sign_in(self):
		settings = frappe.get_single("Anumati Settings")
		settings.staff_two_factor = 1
		settings.save()
		self.assertTrue(frappe.db.get_single_value("System Settings", "enable_two_factor_auth"))
		settings.staff_two_factor = 0
		settings.save()
		self.assertFalse(frappe.db.get_single_value("System Settings", "enable_two_factor_auth"))

	def test_settings_box_off_keeps_two_factor_another_app_needs(self):
		role = "Install Test Host Role"
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "two_factor_auth": 1}).insert()
		self.addCleanup(frappe.delete_doc, "Role", role, force=True, ignore_permissions=True)
		settings = frappe.get_single("Anumati Settings")
		settings.staff_two_factor = 1
		settings.save()
		settings.staff_two_factor = 0
		settings.save()
		self.assertTrue(frappe.db.get_single_value("System Settings", "enable_two_factor_auth"))

	def test_workflow_states_are_added_if_missing_and_never_changed(self):
		frappe.db.set_value("Workflow State", "Draft", "style", "Warning")
		frappe.delete_doc("Workflow Action Master", "Send Back", force=True, ignore_permissions=True)
		install.ensure_workflow_masters()
		self.assertEqual(frappe.db.get_value("Workflow State", "Draft", "style"), "Warning")
		self.assertTrue(frappe.db.exists("Workflow Action Master", "Send Back"))
		for state in install.WORKFLOW_STATES:
			self.assertTrue(frappe.db.exists("Workflow State", state), state)

	def test_no_fixtures_overwrite_shared_records(self):
		shared = {f["dt"] for f in hooks.fixtures}
		for doctype in ("Workflow State", "Workflow Action Master", "Custom DocPerm"):
			self.assertNotIn(doctype, shared)

	def test_notice_audio_script_loads_only_on_notice_forms(self):
		self.assertNotIn("/assets/anumati/js/notice_audio.js", getattr(hooks, "app_include_js", []))
		self.assertEqual(set(hooks.doctype_js), {"Anumati Notice Template", "Anumati Notice Translation"})

	def test_migrate_without_demo_password_does_not_touch_mobile_control(self):
		frappe.conf.pop("anumati_demo_password", None)
		with patch.object(demo, "configure_mobile_app") as configure:
			demo.after_migrate()
		configure.assert_not_called()

	def test_uninstall_list_finds_only_anumati_records(self):
		for doctype, filters in install.UNINSTALL:
			names = frappe.get_all(doctype, filters, pluck="name")
			self.assertTrue(names, doctype)
		for name in frappe.get_all("Custom Field", {"name": ("like", "%-anumati_%")}, ["fieldname"], pluck="fieldname"):
			self.assertTrue(name.startswith("anumati_"), name)

	def test_report_lists_who_opened_anumati_records_only(self):
		for doctype in ("Anumati Programme", "ToDo"):
			log = frappe.get_doc({"doctype": "View Log", "viewed_by": "Administrator",
			                      "reference_doctype": doctype, "reference_name": "INSTALL-TEST"})
			log.flags.ignore_links = True
			log.insert(ignore_permissions=True)
		frappe.set_user(user_with_role("Anumati DPO"))
		try:
			_, rows = report.execute({})
		finally:
			frappe.set_user("Administrator")
		types = {r["record_type"] for r in rows if r["record"] == "INSTALL-TEST"}
		self.assertEqual(types, {"Anumati Programme"})
