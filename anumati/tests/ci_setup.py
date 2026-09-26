"""Helpers for the CI HTTP security check. Run with `bench --site <site> execute ...`.
They refuse to run unless the site has allow_tests set, so they can never touch a real tenant."""

import json
import os
import uuid

import frappe

from anumati.tests.test_permissions import anumati_doctypes, whitelisted


def _guard():
	if not frappe.conf.get("allow_tests"):
		frappe.throw("CI helpers only run on test sites (allow_tests)")


def _write(path, data):
	fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
	with os.fdopen(fd, "w") as fh:
		json.dump(data, fh)


def prepare(path):
	"""Create a DPO API user and one consent event on this tenant; write their handles to `path`."""
	_guard()
	from anumati.tests.utils import make_event

	email = f"ci-dpo-{frappe.local.site.split('.')[0]}@example.com"
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "CI DPO", "send_welcome_email": 0,
			 "roles": [{"role": "Anumati DPO"}]}
		).insert(ignore_permissions=True)
	user = frappe.get_doc("User", email)
	secret = frappe.generate_hash(length=15)
	user.api_key = user.api_key or frappe.generate_hash(length=15)
	user.api_secret = secret
	user.save(ignore_permissions=True)
	event = make_event(event_uuid=str(uuid.uuid4()))
	frappe.db.commit()
	_write(path, {"api_key": user.api_key, "api_secret": secret, "event": event.name, "hash": event.hash})


def inventory(path):
	"""Every Anumati DocType and whitelisted method, for the unauthenticated-route sweep."""
	_guard()
	methods = {m for m in whitelisted() if m.count(".") and not any(p[:1].isupper() for p in m.split("."))}
	_write(path, {"doctypes": anumati_doctypes(), "methods": sorted(methods), "guest": sorted(whitelisted(guest_only=True))})
