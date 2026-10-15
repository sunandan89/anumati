"""Test helpers. All sample data is fictional."""

import uuid
from contextlib import contextmanager

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
	for code in (*kw.get("purposes_granted", ["screen", "follow"]), *kw.get("purposes_denied", ["research"])):
		make_purpose(programme, code, code.title())
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
	doc.flags.anumati_trusted = True  # a ledger fixture, not a capture: the consent rules have their own tests
	doc.insert()
	return doc


@contextmanager
def webhook_call(token=None, ip="203.0.113.10"):
	"""Run a provider callback as a POST with the X-Anumati-Token header from a documentation IP address."""
	from werkzeug.test import EnvironBuilder
	from werkzeug.wrappers import Request

	headers = {"X-Anumati-Token": token} if token else {}
	saved = (getattr(frappe.local, "request", None), getattr(frappe.local, "request_ip", None))
	frappe.local.request = Request(EnvironBuilder(method="POST", headers=headers).get_environ())
	frappe.local.request_ip = ip
	try:
		yield
	finally:
		frappe.local.request, frappe.local.request_ip = saved


def make_evidence(principal_name, content=None, kind="audio", attach_to="Data Principal"):
	"""Upload a private evidence file for a person, as the field app does; returns the event's evidence entry."""
	import hashlib

	content = content or f"fictional voice haan {uuid.uuid4().hex} ".encode() * 20
	f = frappe.get_doc({
		"doctype": "File", "file_name": f"{uuid.uuid4().hex[:8]}-{kind}.m4a", "content": content, "is_private": 1,
		"attached_to_doctype": attach_to, "attached_to_name": principal_name,
	}).insert(ignore_permissions=True)
	return {"file": f.file_url, "kind": kind, "sha256": hashlib.sha256(content).hexdigest()}


def call_webhook(fn, token=None, ip="203.0.113.10", **kwargs):
	with webhook_call(token, ip):
		return fn(**kwargs)
