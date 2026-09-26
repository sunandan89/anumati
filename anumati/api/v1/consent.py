"""Consent API, v1. Served at /api/v2/method/anumati.api.v1.consent.<name> (and /api/method/...).

Phase 0 ships the public verification endpoints; record / withdraw / check / state arrive with the
capture work in Phase 1 (spec section 8)."""

import frappe
from frappe.rate_limiter import rate_limit

from anumati.ledger import keystore, signing


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
@rate_limit(limit=60, seconds=60)
def verify(hash: str, signature: str | None = None):
	"""Verify a consent artefact without seeing any personal data.

	Returns whether the hash is on this tenant's chain, its position, and whether the signature
	(the one given, or the stored one) verifies with the tenant key."""
	row = frappe.db.get_value(
		"Consent Event", {"hash": hash}, ["chain_seq", "key_id", "signature", "server_time"], as_dict=True
	)
	if not row:
		return {"in_chain": False, "signature_valid": False}
	public_b64 = keystore.public_keys().get(row.key_id)
	sig = signature or row.signature
	return {
		"in_chain": True,
		"chain_seq": row.chain_seq,
		"key_id": row.key_id,
		"recorded_at": row.server_time,
		"signature_valid": bool(public_b64) and signing.verify(public_b64, hash, sig),
	}


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=60, seconds=60)
def public_keys():
	"""This tenant's signing public keys, so anyone can verify an export without us (open-source principle)."""
	return keystore.public_keys()
