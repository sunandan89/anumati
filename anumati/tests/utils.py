"""Test helpers. All sample data is fictional."""

import uuid

import frappe


def ensure_language(code="hi", name="Hindi"):
	if not frappe.db.exists("Language", code):
		frappe.get_doc({"doctype": "Language", "language_code": code, "language_name": name}).insert()
	return code


def make_programme(code="TST", name="Test Health Camp"):
	if not frappe.db.exists("Programme", code):
		frappe.get_doc({"doctype": "Programme", "code": code, "programme_name": name}).insert()
	return code


def make_purpose(programme="TST", code="screen", title="Health screening", **kw):
	name = f"{programme}-{code}"
	if not frappe.db.exists("Purpose", name):
		frappe.get_doc(
			{"doctype": "Purpose", "programme": programme, "code": code, "purpose_title": title, **kw}
		).insert()
	return name


def make_principal(ref=None, **kw):
	doc = frappe.get_doc({"doctype": "Data Principal", "principal_ref": ref or f"TST-{uuid.uuid4().hex[:8]}", **kw})
	doc.insert()
	return doc


def make_event(principal=None, programme="TST", **kw):
	make_programme(programme)
	principal = principal or make_principal().name
	doc = frappe.get_doc(
		{
			"doctype": "Consent Event",
			"event_uuid": str(uuid.uuid4()),
			"action": "grant",
			"principal": principal,
			"programme": programme,
			"purposes_granted": ["screen", "follow"],
			"purposes_denied": ["research"],
			"capture_mode": "assisted_thumbprint",
			"channel": "app",
			"captured_by": "Administrator",
			"device_id": "FW-TEST-01",
			"device_time": "2026-09-20 11:20:00",
			"verification_method": "device_sms_otp",
			"verification_status": "recorded",
			**kw,
		}
	)
	doc.insert()
	return doc
