"""Consent API (Phase 1a): record, withdraw, check, state, principal.upsert, notice.get_active.

Covers idempotent sync, out-of-order resolution, the minor/guardian rules, the processing-before-
confirmation gate, and that the API respects stock Frappe permissions. Sample data is fictional."""

import uuid

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests.utils import FrappeTestCase

from anumati import enforcement
from anumati.api.v1 import consent, notice, principal
from anumati.api.schema import SchemaError
from anumati.api.v1.consent import ConsentRequestError
from anumati.tests.utils import ensure_language, make_principal, make_programme, make_purpose

PROG = "API"


def uid():
	return str(uuid.uuid4())


class TestConsentAPI(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_programme(PROG, "API Test Programme")
		make_purpose(PROG, "screen", "Health screening", essential=1)
		make_purpose(PROG, "follow", "Follow-up calls")
		make_purpose(PROG, "research", "Anonymised research", child_allowed=0)

	def setUp(self):
		self.p = make_principal()
		self.ref = self.p.principal_ref

	def grant(self, granted=("screen", "follow"), denied=("research",), **kw):
		return consent.record({
			"event_uuid": kw.pop("event_uuid", uid()), "principal_ref": kw.pop("principal_ref", self.ref),
			"programme": PROG, "purposes_granted": list(granted), "purposes_denied": list(denied),
			"capture_mode": "assisted_thumbprint", "channel": "app", "device_id": "FW-API-01",
			"device_time": kw.pop("device_time", "2026-09-20 11:20:00"), **kw,
		})

	def status(self, code):
		return consent.check(self.ref, code, programme=PROG)

	# -- record -------------------------------------------------------------

	def test_record_returns_signed_artefact_and_projects_state(self):
		art = self.grant()
		self.assertEqual(len(art["hash"]), 64)
		self.assertTrue(art["signature"])
		self.assertEqual(self.status("follow")["status"], "granted")
		self.assertEqual(self.status("research")["status"], "refused")
		self.assertFalse(self.status("research")["allow"])

	def test_replaying_the_same_event_is_idempotent(self):
		event_uuid = uid()
		first = self.grant(event_uuid=event_uuid)
		second = self.grant(event_uuid=event_uuid)
		self.assertEqual(first["hash"], second["hash"])
		self.assertEqual(frappe.db.count("Consent Event", {"event_uuid": event_uuid}), 1)

	def test_unknown_purpose_and_unknown_principal_are_rejected(self):
		self.assertRaises(ConsentRequestError, self.grant, granted=("nope",), denied=())
		self.assertRaises(ConsentRequestError, self.grant, principal_ref="NOT-A-REF")

	def test_withdraw_action_is_refused_on_record(self):
		# Refused by the published schema (action enum) before the handler's own check.
		self.assertRaises((SchemaError, ConsentRequestError), self.grant, action="withdraw")

	# -- withdraw -----------------------------------------------------------

	def test_withdraw_defaults_to_optional_granted_purposes(self):
		self.grant()
		art = consent.withdraw(self.ref, PROG, channel="sms", event_uuid=uid(), device_time="2026-09-21 09:00:00")
		self.assertEqual(art["action"], "withdraw")
		self.assertEqual(self.status("follow")["status"], "withdrawn")
		self.assertEqual(self.status("screen")["status"], "granted", "essential purposes are not withdrawn by default")

	def test_withdraw_specific_purpose(self):
		self.grant()
		consent.withdraw(self.ref, PROG, channel="whatsapp", event_uuid=uid(), purposes=["screen"],
		                 device_time="2026-09-21 09:00:00")
		self.assertEqual(self.status("screen")["status"], "withdrawn")
		self.assertEqual(self.status("follow")["status"], "granted")

	def test_late_arriving_older_event_does_not_override_newer(self):
		# The withdrawal (made later in the field) syncs first; the earlier grant syncs afterwards.
		consent.withdraw(self.ref, PROG, channel="field_worker", event_uuid=uid(), purposes=["follow"],
		                 device_time="2026-09-22 10:00:00")
		self.grant(device_time="2026-09-20 11:20:00")
		self.assertEqual(self.status("follow")["status"], "withdrawn")
		self.assertEqual(self.status("screen")["status"], "granted")

	# -- minors and confirmation ---------------------------------------------

	def test_minor_needs_guardian_and_cannot_grant_child_disallowed_purpose(self):
		child = make_principal(is_minor=1)
		self.assertRaises(ConsentRequestError, self.grant, principal_ref=child.principal_ref, denied=())
		guardian = make_principal()
		link = frappe.get_doc({"doctype": "Guardian Link", "principal": child.name, "guardian": guardian.name,
		                       "guardian_type": "parent", "verification_method": "device_sms_otp"}).insert()
		self.assertRaises(ConsentRequestError, self.grant, principal_ref=child.principal_ref,
		                  granted=("screen", "research"), denied=(), guardian_link=link.name)
		art = self.grant(principal_ref=child.principal_ref, denied=("research",), guardian_link=link.name,
		                 capture_mode="guardian_minor")
		self.assertTrue(art["hash"])
		verdict = consent.check(child.principal_ref, "follow", programme=PROG)
		self.assertFalse(verdict["allow"], "minors are never processed before confirmation")
		self.assertEqual(verdict["status"], "awaiting_confirmation")

	def test_processing_before_confirmation_follows_programme_setting(self):
		self.grant()
		self.assertTrue(self.status("follow")["allow"])
		frappe.db.set_value("Programme", PROG, "allow_processing_before_confirm", 0)
		frappe.clear_document_cache("Programme", PROG)
		try:
			self.assertFalse(self.status("follow")["allow"])
			other = make_principal()
			self.grant(principal_ref=other.principal_ref, verification_status="confirmed")
			self.assertTrue(consent.check(other.principal_ref, "follow", programme=PROG)["allow"])
		finally:
			frappe.db.set_value("Programme", PROG, "allow_processing_before_confirm", 1)
			frappe.clear_document_cache("Programme", PROG)

	def test_check_unknown_principal_denies(self):
		verdict = consent.check("NO-SUCH-PERSON", "follow", programme=PROG)
		self.assertFalse(verdict["allow"])
		self.assertEqual(verdict["status"], "unknown_principal")

	# -- state, rebuild ------------------------------------------------------

	def test_state_lists_every_purpose(self):
		self.grant()
		rows = {r["purpose"]: r["status"] for r in consent.state(self.ref, programme=PROG)}
		self.assertEqual(rows, {f"{PROG}-screen": "granted", f"{PROG}-follow": "granted", f"{PROG}-research": "refused"})

	def test_projection_rebuilds_identically_from_the_ledger(self):
		self.grant()
		consent.withdraw(self.ref, PROG, channel="sms", event_uuid=uid(), device_time="2026-09-21 09:00:00")
		before = consent.state(self.ref)
		enforcement.rebuild(self.p.name)
		self.assertEqual([(r["purpose"], r["status"]) for r in consent.state(self.ref)],
		                 [(r["purpose"], r["status"]) for r in before])

	# -- permissions ---------------------------------------------------------

	def test_guest_cannot_record_or_check(self):
		frappe.set_user("Guest")
		try:
			self.assertRaises(frappe.PermissionError, self.grant)
			self.assertRaises(frappe.PermissionError, consent.check, self.ref, "follow", PROG)
		finally:
			frappe.set_user("Administrator")


class TestPrincipalAndNoticeAPI(FrappeTestCase):
	def test_upsert_creates_then_updates_without_echoing_pii(self):
		ref = f"UPS-{uuid.uuid4().hex[:6]}"
		out = principal.upsert(ref, full_name="Meena K. (fictional)", phone="9000011111")
		self.assertEqual(out, {"principal_ref": ref, "created": True})
		out = principal.upsert(ref, preferred_language=None, shared_phone=1)
		self.assertFalse(out["created"])
		doc = frappe.get_doc("Data Principal", {"principal_ref": ref})
		self.assertTrue(doc.shared_phone)
		self.assertTrue(doc.phone_hash)
		self.assertEqual(doc.get_password("full_name"), "Meena K. (fictional)")

	def test_get_active_serves_published_notice_and_only_reviewed_translations(self):
		make_programme("NTC", "Notice API Programme")
		purpose = make_purpose("NTC", "screen", "Health screening")
		if not frappe.db.exists("Data Category", "Health readings"):
			frappe.get_doc({"doctype": "Data Category", "category_name": "Health readings"}).insert()
		ropa = frappe.get_doc({"doctype": "ROPA Entry", "purpose": purpose, "retention": "24 months",
		                       "safeguards": "Encrypted", "data_categories": [{"data_category": "Health readings"}]}).insert()
		apply_workflow(ropa, "Approve")
		doc = frappe.get_doc({
			"doctype": "Notice Template", "programme": "NTC", "version": "1.0.0", "summary": "We screen your health.",
			"purposes": [{"purpose": purpose}], "withdrawal_methods": "SMS STOP", "rights_text": "Access, correction",
			"board_complaint_route": "Data Protection Board", "dpo_contact": "DPO (fictional)",
			"security_summary": "Encrypted",
		}).insert()
		apply_workflow(doc, "Publish")
		ensure_language("en", "English")
		frappe.get_doc({"doctype": "Notice Translation", "notice": doc.name, "language": "en",
		                "summary": "Machine draft", "machine_translated": 1}).insert()
		out = notice.get_active("NTC", language="en")
		self.assertEqual(out["version"], "1.0.0")
		self.assertEqual(out["purposes"][0]["code"], "screen")
		self.assertIsNone(out["translation"], "an unreviewed translation must not be served")
