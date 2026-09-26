"""Tenant signing keys.

Resolution order for the active key:
  1. site config `anumati_signing_key` (base64 raw Ed25519 private key) — for ops-managed or KMS-fed keys
  2. Anumati Settings `signing_private_key` (Password field, encrypted with the site's encryption key),
     generated on install

Public keys for verification = the active key + Anumati Settings `retired_signing_keys`
+ site config `anumati_retired_public_keys` ({key_id: public_b64}). Keys are never logged.
"""

import json

import frappe
from frappe.utils.password import get_decrypted_password

from anumati.ledger import signing

SETTINGS = "Anumati Settings"


def _settings_private_key() -> str | None:
	return get_decrypted_password(SETTINGS, SETTINGS, "signing_private_key", raise_exception=False)


def active_key() -> tuple[str, str]:
	"""Return (key_id, private_b64). Throws if the tenant has no key yet."""
	cached = getattr(frappe.local, "anumati_active_key", None)
	if cached:
		return cached
	private_b64 = frappe.conf.get("anumati_signing_key") or _settings_private_key()
	if not private_b64:
		frappe.throw("Anumati signing key is not set up. Run migrate or reinstall the app.")
	key_id = signing.key_id_for(signing.public_from_private(private_b64))
	frappe.local.anumati_active_key = (key_id, private_b64)
	return frappe.local.anumati_active_key


def public_keys() -> dict[str, str]:
	"""All keys that may verify a signature on this tenant, {key_id: public_b64}."""
	keys = {}
	retired = frappe.db.get_single_value(SETTINGS, "retired_signing_keys")
	if retired:
		keys.update(json.loads(retired) if isinstance(retired, str) else retired)
	keys.update(frappe.conf.get("anumati_retired_public_keys") or {})
	try:
		key_id, private_b64 = active_key()
		keys[key_id] = signing.public_from_private(private_b64)
	except frappe.ValidationError:
		pass
	return keys


def clear_cache():
	frappe.local.anumati_active_key = None


def ensure_keys():
	"""Create the tenant signing key and phone-hash salt if missing. Idempotent; never rotates."""
	settings = frappe.get_single(SETTINGS)
	changed = False
	if not _settings_private_key() and not frappe.conf.get("anumati_signing_key"):
		private_b64, public_b64, key_id = signing.generate_keypair()
		settings.signing_private_key = private_b64
		settings.signing_public_key = public_b64
		settings.signing_key_id = key_id
		changed = True
	if not get_decrypted_password(SETTINGS, SETTINGS, "phone_hash_salt", raise_exception=False):
		settings.phone_hash_salt = frappe.generate_hash(length=64)
		changed = True
	if changed:
		settings.flags.ignore_permissions = True
		settings.flags.ignore_mandatory = True
		settings.save()
	clear_cache()


def rotate():
	"""Retire the active settings key (its public half keeps verifying old events) and create a new one."""
	if frappe.conf.get("anumati_signing_key"):
		frappe.throw("This site's signing key comes from site config; rotate it there.")
	settings = frappe.get_single(SETTINGS)
	retired = json.loads(settings.retired_signing_keys or "{}")
	old_private = _settings_private_key()
	if old_private:
		old_public = signing.public_from_private(old_private)
		retired[signing.key_id_for(old_public)] = old_public
	private_b64, public_b64, key_id = signing.generate_keypair()
	settings.signing_private_key = private_b64
	settings.signing_public_key = public_b64
	settings.signing_key_id = key_id
	settings.retired_signing_keys = json.dumps(retired, sort_keys=True)
	settings.flags.ignore_permissions = True
	settings.save()
	clear_cache()
	return key_id
