"""Canonical JSON and hashing for the Anumati ledgers.

Pure Python (no Frappe import) so the same code can verify an exported chain outside Frappe.

    hash = sha256(canonical_json(payload) + prev_hash)

payload holds only the fields listed in the chain's schema, each normalised to a fixed type, so a
row read back from MariaDB hashes to the same value it was sealed with.
"""

import hashlib
import json
from datetime import date, datetime

GENESIS_HASH = "0" * 64


def canonical_json(obj) -> bytes:
	return json.dumps(
		obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
	).encode("utf-8")


def normalise(value, kind: str):
	"""Coerce a field value to its canonical form. kind is one of str, int, datetime, json."""
	if kind == "int":
		return int(value or 0)
	if value is None or value == "":
		return None
	if kind == "str":
		return str(value)
	if kind == "datetime":
		if isinstance(value, str):
			value = datetime.fromisoformat(value.strip())
		elif isinstance(value, date) and not isinstance(value, datetime):
			value = datetime(value.year, value.month, value.day)
		if value.tzinfo is not None:
			raise ValueError("ledger datetimes must be naive, in the site time zone")
		return value.strftime("%Y-%m-%d %H:%M:%S.%f")
	if kind == "json":
		if isinstance(value, bytes | str):
			value = json.loads(value)
		return value
	raise ValueError(f"unknown field kind {kind!r}")


def to_storage(value, kind: str):
	"""The exact value to write to the database for a normalised field."""
	value = normalise(value, kind)
	if kind == "json" and value is not None:
		return canonical_json(value).decode("utf-8")
	return value


def payload(schema: dict, getter) -> dict:
	"""Build the hashed payload. schema maps fieldname -> kind; getter(fieldname) returns the value."""
	return {field: normalise(getter(field), kind) for field, kind in schema.items()}


def compute_hash(payload_dict: dict, prev_hash: str) -> str:
	return hashlib.sha256(canonical_json(payload_dict) + prev_hash.encode("ascii")).hexdigest()


def digest_text(text: str | None) -> str | None:
	"""SHA-256 of a secret value (e.g. witness details) so it can be chained without storing it in clear."""
	if not text:
		return None
	return hashlib.sha256(text.encode("utf-8")).hexdigest()
