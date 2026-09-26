"""Notice publish gate (spec v0.4, T18): a notice cannot go live until every purpose has an approved
record of processing, with a completed DPIA where one is required. Enforced by stock Frappe Workflows
shipped as fixtures."""

import frappe
from frappe.model.workflow import WorkflowTransitionError, apply_workflow
from frappe.tests.utils import FrappeTestCase

from anumati.tests.utils import make_programme, make_purpose

RULE3 = {
	"withdrawal_methods": "Missed call, SMS STOP, or tell any worker",
	"rights_text": "Ask for a copy, a correction or erasure",
	"board_complaint_route": "Data Protection Board of India",
	"dpo_contact": "DPO, Test Foundation (fictional)",
	"security_summary": "Encrypted, access logged",
}


def make_notice(purpose, version="1.0.0", **kw):
	return frappe.get_doc(
		{"doctype": "Notice Template", "programme": "WFT", "version": version,
		 "purposes": [{"purpose": purpose}], **RULE3, **kw}
	).insert()


def make_ropa(purpose, **kw):
	if not frappe.db.exists("Data Category", "Health readings"):
		frappe.get_doc({"doctype": "Data Category", "category_name": "Health readings", "is_sensitive": 1}).insert()
	return frappe.get_doc(
		{"doctype": "ROPA Entry", "purpose": purpose, "data_categories": [{"data_category": "Health readings"}],
		 "retention": "24 months", "safeguards": "Encrypted; access logged", **kw}
	).insert()


class TestPublishGate(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_programme("WFT", "Workflow Test Programme")

	def test_publish_blocked_without_ropa(self):
		notice = make_notice(make_purpose("WFT", "noropa", "No ROPA yet"))
		self.assertRaises(WorkflowTransitionError, apply_workflow, notice, "Publish")

	def test_publish_blocked_without_rule3_contents(self):
		purpose = make_purpose("WFT", "r3", "Rule 3 check")
		apply_workflow(make_ropa(purpose), "Approve")
		notice = make_notice(purpose, version="1.0.1", security_summary=None)
		self.assertRaises(WorkflowTransitionError, apply_workflow, notice, "Publish")

	def test_publish_allowed_with_approved_ropa(self):
		purpose = make_purpose("WFT", "ok", "Health screening")
		apply_workflow(make_ropa(purpose), "Approve")
		notice = apply_workflow(make_notice(purpose, version="2.0.0"), "Publish")
		self.assertEqual(notice.status, "Published")
		self.assertEqual(notice.docstatus, 1)

	def test_dpia_required_blocks_ropa_approval_until_complete(self):
		purpose = make_purpose("WFT", "research", "Anonymised research", dpia_required=1)
		ropa = make_ropa(purpose)
		self.assertTrue(ropa.dpia_required)
		self.assertRaises(WorkflowTransitionError, apply_workflow, ropa, "Approve")
		ropa.update(
			{"dpia_necessity": "Plan camp locations", "dpia_minimisation": "Age bands only",
			 "dpia_risks": "Re-identification", "dpia_safeguards": "Minors excluded",
			 "dpia_residual_risk": "Low", "dpo_approval": 1}
		)
		ropa.save()
		self.assertEqual(apply_workflow(ropa, "Approve").status, "Approved")
