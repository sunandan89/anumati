"""API contract (Phase 1e): every endpoint is in the published OpenAPI file, writes are validated against
its JSON Schemas without echoing values, and the polling feed mirrors webhook events without PII."""

import importlib
import json
import pkgutil
import uuid

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

import anumati.api.v1 as v1
from anumati.api import schema
from anumati.api.v1 import consent, notifications, principal
from anumati.tests.utils import make_principal, make_programme, make_purpose


def published_paths():
	with open(frappe.get_app_path("anumati", "public", "openapi.json")) as fh:
		return set(json.load(fh)["paths"])


class TestAPIContract(FrappeTestCase):
	def test_every_endpoint_is_documented(self):
		for mod in pkgutil.iter_modules(v1.__path__):
			importlib.import_module(f"anumati.api.v1.{mod.name}")
		endpoints = {
			f"/api/v2/method/{fn.__module__}.{fn.__qualname__}"
			for fn in frappe.whitelisted if fn.__module__.startswith("anumati.api.v1.")
		}
		self.assertTrue(endpoints, "no endpoints found")
		self.assertEqual(endpoints - published_paths(), set(), "add these to tools/gen_openapi.py")

	def test_unknown_or_malformed_fields_are_rejected_without_echoing_values(self):
		with self.assertRaises(schema.SchemaError) as ctx:
			consent.record({"event_uuid": str(uuid.uuid4()), "principal_ref": "X", "programme": "P",
			                "phone_number": "9000055555", "capture_mode": "telepathy"})
		message = str(ctx.exception)
		self.assertIn("phone_number", message)
		self.assertNotIn("9000055555", message)
		self.assertNotIn("telepathy", message)
		self.assertRaises(schema.SchemaError, principal.upsert, "REF-1", is_minor="maybe")
		self.assertRaises(schema.SchemaError, consent.record, {"principal_ref": "X", "programme": "P"})

	def test_feed_mirrors_consent_events_without_pii(self):
		make_programme("FEED", "Feed Test Programme")
		make_purpose("FEED", "follow", "Follow-up calls")
		p = make_principal(full_name="Sita R. (fictional)", phone="9000066666")
		since = add_to_date(now_datetime(), seconds=-5)
		art = consent.record({"event_uuid": str(uuid.uuid4()), "principal_ref": p.principal_ref, "programme": "FEED",
		                      "purposes_granted": ["follow"], "channel": "api"})
		out = notifications.feed(str(since))
		mine = [e for e in out["events"] if e.get("consent_id") == art["consent_id"]]
		self.assertEqual(len(mine), 1)
		self.assertEqual(mine[0]["event"], "consent.recorded")
		self.assertEqual(mine[0]["principal_ref"], p.principal_ref)
		dump = json.dumps(out, default=str)
		self.assertNotIn("Sita", dump)
		self.assertNotIn("9000066666", dump)
