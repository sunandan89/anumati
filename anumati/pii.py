"""PII helpers. Names, phones and witness details are stored in Frappe Password fields (encrypted with
the site's encryption key); lookups use a salted HMAC of the normalised phone number. Nothing here logs
values."""

import hashlib
import hmac
import re

import frappe
from frappe.utils.password import get_decrypted_password


def is_dummy(value) -> bool:
	"""Frappe replaces a saved Password value with asterisks; those must never be re-hashed."""
	return bool(value) and set(str(value)) == {"*"}


def normalise_phone(phone: str) -> str:
	"""Digits only; Indian numbers reduced to their 10-digit national form."""
	digits = re.sub(r"\D", "", phone or "")
	if len(digits) == 12 and digits.startswith("91"):
		digits = digits[2:]
	elif len(digits) == 11 and digits.startswith("0"):
		digits = digits[1:]
	return digits


def _salt() -> str:
	salt = frappe.conf.get("anumati_phone_salt") or get_decrypted_password(
		"Anumati Settings", "Anumati Settings", "phone_hash_salt", raise_exception=False
	)
	if not salt:
		frappe.throw("Anumati phone-hash salt is not set up. Run migrate or reinstall the app.")
	return salt


def phone_hash(phone: str | None) -> str | None:
	digits = normalise_phone(phone or "")
	if not digits:
		return None
	return hmac.new(_salt().encode(), digits.encode(), hashlib.sha256).hexdigest()


def sync_hash(doc, secret_field: str, hash_field: str):
	"""Keep hash_field in step with an encrypted phone field on save."""
	value = doc.get(secret_field)
	if is_dummy(value):
		return  # unchanged since last save
	doc.set(hash_field, phone_hash(value) if value else None)
