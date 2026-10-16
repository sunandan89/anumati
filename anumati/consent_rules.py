"""Consent rules, enforced by the Consent Event DocType itself (solution document: "rules live in the
DocType, not the endpoint").

Every new Consent Event goes through `prepare` in the controller's before_insert, however it arrives:
consent.record / consent.withdraw, the Frappe Mobile SDK's standard sync (frappe.client.insert), plain
REST, Desk or a host app's Python. So the rules are the same for all of them.

Server code that has already decided everything itself (the self-service page, test fixtures) sets
`doc.flags.anumati_trusted` and only gets its event_uuid checked."""

import json

import frappe
from frappe import _

from anumati import enforcement, evidence

ACTIONS = ("grant", "refuse", "renew", "withdraw")
CLIENT_VERIFICATION = ("recorded", "confirmed", "evidence_only")
GUARDIAN_FOR_ADULT = ("legal_guardian", "court", "committee", "family_pwd")
# Set only by the server when it seals the event; whatever a client sends for them is dropped.
SERVER_FIELDS = ("server_time", "chain_seq", "prev_hash", "hash", "signature", "key_id", "short_code",
                 "witness_digest", "notice_version")


class ConsentRequestError(frappe.ValidationError):
	pass


def _codes(value) -> list:
	if not value:
		return []
	return list(json.loads(value) if isinstance(value, str) else value)


def check_purposes(programme: str, principal: str, granted: list, denied: list):
	if set(granted) & set(denied):
		frappe.throw(_("A purpose cannot be both granted and denied"), ConsentRequestError)
	person = frappe.db.get_value("Data Principal", principal, ["is_minor", "renewal_due"], as_dict=True)
	if not person:
		frappe.throw(_("Unknown beneficiary {0}").format(principal), ConsentRequestError)
	is_minor = person.is_minor and not person.renewal_due
	for code in granted + denied:
		row = frappe.db.get_value("Purpose", enforcement.purpose_name(programme, code), ["child_allowed"], as_dict=True)
		if not row:
			frappe.throw(_("Unknown purpose {0} for programme {1}").format(code, programme), ConsentRequestError)
		if is_minor and code in granted and not row.child_allowed:
			frappe.throw(_("Purpose {0} is not allowed for minors").format(code), ConsentRequestError)


def check_who(principal: str, action: str, event):
	"""Who may consent, and what each journey must carry (the field app enforces the same rules):
	- a child under 18 (still a child on record): a guardian link; a guardian other than a parent needs the
	  order number that appointed them;
	- an adult who can't decide alone (pwd_guarded): a lawful guardian link with the order number;
	- an adult who needs help to read the notice, consenting for themselves: a witness.
	A child who turned 18 (renewal_due) consents for themselves, so no guardian is needed."""
	person = frappe.db.get_value("Data Principal", principal,
	                             ["is_minor", "pwd_guarded", "needs_assistance", "renewal_due"], as_dict=True)
	child = person.is_minor and not person.renewal_due
	if child or person.pwd_guarded:
		if not event.guardian_link:
			frappe.throw(_("A child's consent needs a verified guardian_link (spec C1)") if child else
			             _("An adult who can't decide alone needs a lawful guardian_link"), ConsentRequestError)
		link = frappe.db.get_value("Guardian Link", event.guardian_link, ["principal", "guardian_type", "authority_ref"],
		                           as_dict=True)
		if not link or link.principal != principal:
			frappe.throw(_("guardian_link must be a Guardian Link for this person"), ConsentRequestError)
		if (person.pwd_guarded and not child) or link.guardian_type != "parent":
			if not (link.authority_ref or "").strip():
				frappe.throw(_("This guardian needs the number of the order that appointed them (authority_ref)"),
				             ConsentRequestError)
			if not child and link.guardian_type not in GUARDIAN_FOR_ADULT:
				frappe.throw(_("Only a guardian appointed by a court or the Local Level Committee can consent for an adult"),
				             ConsentRequestError)
	elif person.needs_assistance and action in ("grant", "renew") and not (event.witness or "").strip():
		frappe.throw(_("Someone who needs help to read the notice needs a witness"), ConsentRequestError)
	if action in ("grant", "renew") and event.verification_method == "device_sms_otp":
		# The worker sees a code sent from their own phone, so it can't stand alone: the person's (or the
		# guardian's) recorded "haan" must come with it.
		if not any((e or {}).get("kind") == "audio" for e in _codes(event.evidence)):
			frappe.throw(_("A code sent from the worker's phone needs the recorded voice 'haan' with it"),
			             ConsentRequestError)
	return person


def verification_status(event, principal) -> str:
	"""Only the server decides how far a consent is verified (review C2). A phone or host system can never
	set "confirmed": that comes only from the server's own code check (verification.verify_otp) or a
	delivery report. "evidence_only" needs at least one evidence file that checks out (C3), or the guardian's
	order or ID uploaded for this person; without it the consent is just "recorded"."""
	if event.verification_status and event.verification_status not in CLIENT_VERIFICATION:
		frappe.throw(_("verification_status must be one of {0}").format(", ".join(CLIENT_VERIFICATION)), ConsentRequestError)
	try:
		checked = evidence.check_event_evidence(principal, _codes(event.evidence), event.guardian_link)
	except evidence.EvidenceError as e:
		frappe.throw(str(e), ConsentRequestError)
	if event.action != "withdraw" and event.verification_method == "evidence_only" and (
			checked or evidence.guardian_link_has_evidence(event.guardian_link, principal)):
		return "evidence_only"
	return "recorded"


def prepare(doc):
	"""before_insert of every Consent Event: identity, then (unless trusted) every rule."""
	# The Frappe Mobile SDK names a record by its phone-made mobile_uuid (a Mobile Control custom field);
	# it becomes the event_uuid, so the record's name, its receipt code and the SDK's retry all agree.
	doc.event_uuid = (doc.event_uuid or doc.get("mobile_uuid") or "").strip()
	if not doc.event_uuid:
		frappe.throw(_("event_uuid is required"), ConsentRequestError)
	if doc.flags.anumati_trusted:
		return

	for field in SERVER_FIELDS:
		doc.set(field, None)
	doc.captured_by = frappe.session.user
	doc.action = doc.action or "grant"
	if doc.action not in ACTIONS:
		frappe.throw(_("action must be one of {0}").format(", ".join(ACTIONS)), ConsentRequestError)
	if not doc.principal or not frappe.db.exists("Data Principal", doc.principal):
		frappe.throw(_("Unknown beneficiary {0}").format(doc.principal), ConsentRequestError)
	if not doc.programme or not frappe.db.exists("Programme", doc.programme):
		frappe.throw(_("Unknown programme {0}").format(doc.programme), ConsentRequestError)

	granted, denied = _codes(doc.purposes_granted), _codes(doc.purposes_denied)
	if doc.action == "refuse":
		granted, denied = [], denied or granted
	elif doc.action == "withdraw":
		granted, denied = [], denied or granted
	doc.purposes_granted, doc.purposes_denied = granted, denied
	check_purposes(doc.programme, doc.principal, granted, denied)
	if doc.action != "withdraw":
		check_who(doc.principal, doc.action, doc)

	if doc.notice:
		notice = frappe.db.get_value("Notice Template", doc.notice, ["programme", "version", "docstatus"], as_dict=True)
		if not notice or notice.programme != doc.programme or notice.docstatus != 1:
			frappe.throw(_("notice must be a published notice of this programme"), ConsentRequestError)
		doc.notice_version = notice.version
	doc.verification_status = verification_status(doc, doc.principal)


def after_insert(doc):
	"""What a new event changes beyond the ledger, the same for every door it came through."""
	evidence.adopt_uploads(doc.principal, _codes(doc.evidence), doc.captured_by)
	granted = _codes(doc.purposes_granted)
	if granted and frappe.db.get_value("Data Principal", doc.principal, "relationship_ended_on") and _rejoined(
			doc.principal, doc.programme, granted):
		# They rejoined a programme: the relationship is live again.
		frappe.db.set_value("Data Principal", doc.principal, "relationship_ended_on", None)
		frappe.get_doc("Data Principal", doc.principal).add_comment(
			"Info", _("Rejoined programme {0}: relationship live again").format(doc.programme))
	if (doc.action in ("grant", "renew") and not doc.guardian_link
			and frappe.db.get_value("Data Principal", doc.principal, "renewal_due")):
		# A child who turned 18 has now consented themselves: they are an adult record from here on.
		person = frappe.get_doc("Data Principal", doc.principal)
		person.db_set({"renewal_due": 0, "is_minor": 0})
		frappe.clear_document_cache("Data Principal", doc.principal)
		enforcement.invalidate(doc.principal)


def _rejoined(principal, programme, granted) -> bool:
	"""An essential purpose of this event is granted now. An older grant that arrives after they left is
	ignored by enforcement (a newer decision wins), so it must not end "Relationship ended" either."""
	essential = frappe.get_all(
		"Purpose", {"name": ("in", [enforcement.purpose_name(programme, c) for c in granted]), "essential": 1},
		pluck="name")
	if not essential:
		return False
	enforcement.invalidate(principal)
	states = enforcement.states_for(principal)
	return any(states.get(name, {}).get("status") == "granted" for name in essential)
