"""Validate API input against the published JSON Schemas in anumati/public/openapi.json (spec T5).

Error messages name the field and the rule, never the submitted value, so a bad phone number or name
is not echoed back or logged."""

import json
from functools import lru_cache

import frappe
from frappe import _
from jsonschema import Draft202012Validator


class SchemaError(frappe.ValidationError):
	pass


@lru_cache(maxsize=1)
def _schemas() -> dict:
	with open(frappe.get_app_path("anumati", "public", "openapi.json")) as fh:
		return json.load(fh)["components"]["schemas"]


@lru_cache(maxsize=None)
def _validator(name: str) -> Draft202012Validator:
	return Draft202012Validator(_schemas()[name])


def validate(name: str, payload: dict):
	errors = sorted(_validator(name).iter_errors(payload), key=lambda e: list(e.path))
	if errors:
		problems = []
		for err in errors[:5]:
			field = ".".join(str(p) for p in err.path) or "request"
			if err.validator == "required":
				missing = [r for r in err.validator_value if r not in (err.instance or {})]
				problems.append(_("missing field(s): {0}").format(", ".join(missing)))
				continue
			if err.validator == "additionalProperties":
				extra = sorted(set(err.instance) - set(err.schema.get("properties", {})))
				problems.append(_("unknown field(s): {0}").format(", ".join(extra)))
			else:
				problems.append(_("{0}: fails '{1}'").format(field, err.validator))
		frappe.throw(_("Invalid request: {0}").format("; ".join(problems)), SchemaError)
