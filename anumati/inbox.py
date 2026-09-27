"""Withdrawal & rights inbox: match an incoming request to a principal (spec section 6).

Matching never exposes personal data: requests carry a salted phone hash or a consent short code, and
candidates are listed by principal_ref only. A shared number that maps to several people is left for a
person to resolve (status Unmatched), with the SLA clock already running from receipt."""

import frappe


def principals_for_phone_hash(phone_hash: str) -> list[dict]:
	if not phone_hash:
		return []
	return frappe.get_all(
		"Data Principal", {"phone_hash": phone_hash, "merged_into": ("is", "not set")}, ["name", "principal_ref"]
	)


def event_for_short_code(code: str) -> tuple[str | None, str | None]:
	"""Resolve a receipt code (AN-XXXXXX, with or without the prefix) to (principal, programme)."""
	code = (code or "").strip().upper()
	if code and not code.startswith("AN-"):
		code = "AN-" + code
	row = frappe.db.get_value("Consent Event", {"short_code": code}, ["principal", "programme"], as_dict=True) if code else None
	return (row.principal, row.programme) if row else (None, None)


def principal_for_short_code(code: str) -> str | None:
	return event_for_short_code(code)[0]


def match(request):
	"""Fill matched_principal / match_confidence / candidates / status on a Rights Request, in place."""
	if request.matched_principal:
		request.match_confidence = request.match_confidence or 100
		request.candidates = None
		if request.status == "Unmatched":
			request.status = "Open"
		return
	found = principals_for_phone_hash(request.sender_hash)
	if len(found) == 1:
		request.matched_principal, request.match_confidence, request.candidates = found[0].name, 90, None
	elif len(found) > 1:
		request.status = "Unmatched"
		request.match_confidence = 0
		request.candidates = ", ".join(sorted(p.principal_ref or p.name for p in found))
	elif request.channel in ("sms", "missed_call", "ivr", "whatsapp") and request.status == "Open":
		request.status = "Unmatched"
