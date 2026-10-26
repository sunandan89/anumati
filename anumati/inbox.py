"""Withdrawal & rights inbox: match an incoming request to a principal (spec section 6).

Matching never exposes personal data: requests carry a salted phone hash or a consent short code, and
candidates are listed by principal_ref only. A shared number that maps to several people is left for a
person to resolve (status "Who is this?"), with the reply-by clock already running from receipt."""

import frappe

# Rights Request statuses (plain words; the same ones the person sees on the self-service page).
NEW, WHO, WORKING, WAITING_PERSON, WAITING_PARTNERS = (
	"new_request", "who_is_this", "working_on_it", "waiting_for_person", "waiting_for_partners")
ANSWERED, CLOSED, CANNOT = "request_answered", "request_closed", "cannot_do"
DONE = (ANSWERED, CLOSED, CANNOT)  # nothing more for staff to do; the reply-by clock stops


def principals_for_phone_hash(phone_hash: str) -> list[dict]:
	if not phone_hash:
		return []
	owners = frappe.get_all(
		"Anumati Data Principal", {"phone_hash": phone_hash, "merged_into": ("is", "not set")}, ["name", "principal_ref"]
	)
	# A parent's or guardian's number also finds the people they consented for (a child has no phone of
	# their own in the field app), so "STOP" or a missed call from the guardian reaches the right record.
	wards = frappe.get_all("Anumati Guardian Link", {"guardian": ("in", [o.name for o in owners] or ["-"])}, pluck="principal")
	seen = {o.name for o in owners}
	for ward in frappe.get_all("Anumati Data Principal", {"name": ("in", wards or ["-"]), "merged_into": ("is", "not set")},
	                           ["name", "principal_ref"]):
		if ward.name not in seen:
			owners.append(ward)
			seen.add(ward.name)
	return owners


def event_for_short_code(code: str, phone_hash: str | None = None) -> tuple[str | None, str | None]:
	"""Resolve a receipt code (AN-XXXXXX, with or without the prefix) to (principal, programme).

	Codes are 30 bits, so two people can share one. If they do, the sender's phone hash picks the
	right person; without it (or if it doesn't settle it) nothing is returned and a person resolves it."""
	code = (code or "").strip().upper()
	if code and not code.startswith("AN-"):
		code = "AN-" + code
	if not code:
		return (None, None)
	rows = frappe.get_all("Anumati Consent Event", {"short_code": code}, ["principal", "programme"],
	                      order_by="chain_seq desc")
	people = {r.principal for r in rows}
	if len(people) > 1 and phone_hash:
		mine = {p.name for p in principals_for_phone_hash(phone_hash)} & people
		rows = [r for r in rows if r.principal in mine]
		people = {r.principal for r in rows}
	if len(people) != 1:
		return (None, None)
	return (rows[0].principal, rows[0].programme)


def principal_for_short_code(code: str, phone_hash: str | None = None) -> str | None:
	return event_for_short_code(code, phone_hash)[0]


def match(request):
	"""Fill matched_principal / match_confidence / candidates / status on a Rights Request, in place."""
	if request.matched_principal:
		request.match_confidence = request.match_confidence or 100
		request.candidates = None
		if request.status == WHO:
			request.status = NEW
		return
	found = principals_for_phone_hash(request.sender_hash)
	if len(found) == 1:
		request.matched_principal, request.match_confidence, request.candidates = found[0].name, 90, None
	elif len(found) > 1:
		request.status = WHO
		request.match_confidence = 0
		request.candidates = ", ".join(sorted(p.principal_ref or p.name for p in found))
	elif request.channel in ("sms", "missed_call", "ivr", "whatsapp") and request.status == NEW:
		request.status = WHO
