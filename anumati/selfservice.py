"""Self-service page (/my-consent): a person sees and changes their own choices, gets their receipts, and
asks us things, without an app or a Frappe login.

Sign-in, two ways:
- **Phone + SMS code.** The code goes only to a number we hold; it lives in Redis for 10 minutes (only its
  hash), with 5 tries and 3 codes per number per 10 minutes. The person sees themselves and the people they
  are guardian for. When several adults share the number, they pick their name and confirm their year of
  birth, so nobody can act for another adult on the same phone.
- **Receipt code + year of birth**, for people without a phone. A slip can be lost or seen, so this way can
  only turn uses off, leave, and ask us things; agreeing to anything new needs the SMS code or a field worker.

A signed-in visit is a random token in an HttpOnly, SameSite=Strict cookie; the session (who may be seen
and changed) lives in Redis for 15 minutes of inactivity. Beneficiaries are not Frappe users: nothing is
stored in the User list, and names and numbers stay encrypted. Responses carry only the person's own data.
Changes are signed Consent Events (channel "web"), exactly like a change in the field app."""

import hashlib
import hmac
import secrets
import uuid

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, getdate, now_datetime

from anumati import channels, conversation, enforcement, grievance, inbox, pii
from anumati.api.v1 import consent
from anumati.api.v1.principal import mask_phone

COOKIE = "anumati_ss"
SESSION_SECONDS = 15 * 60
CODE_SECONDS = 10 * 60
MAX_TRIES = 5
MAX_SENDS = 3
RIGHTS = ("access", "correction", "erasure", "nomination")
GUARDIAN_MODES = {"child": "guardian_minor", "guarded": "guardian_pwd"}


class SignInError(frappe.AuthenticationError):
	http_status_code = 401


# ------------------------------------------------------------------ session


def _get(key: str):
	"""Read straight from Redis: these values change within one request, so Frappe's per-request copy of
	earlier reads must not answer."""
	return frappe.cache.get_value(key, expires=True)


def _skey(token: str) -> str:
	return "anumati:ss:" + hashlib.sha256(token.encode()).hexdigest()


def _token_in() -> str | None:
	if frappe.flags.in_test:
		return frappe.flags.anumati_ss  # tests call the functions directly
	request = getattr(frappe.local, "request", None)
	return request.cookies.get(COOKIE) if request is not None else None


def _new_session(data: dict) -> str:
	old = _token_in()
	if old:
		frappe.cache.delete_value(_skey(old))
	token = secrets.token_urlsafe(32)
	frappe.cache.set_value(_skey(token), data, expires_in_sec=SESSION_SECONDS)
	if getattr(frappe.local, "cookie_manager", None):
		frappe.local.cookie_manager.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite="Strict")
	frappe.flags.anumati_ss = token
	return token


def _session() -> dict:
	token = _token_in()
	data = _get(_skey(token)) if token else None
	if not data:
		raise SignInError(_("Please sign in again."))
	frappe.cache.set_value(_skey(token), data, expires_in_sec=SESSION_SECONDS)  # 15 minutes from the last use
	return data


def _save(data: dict):
	frappe.cache.set_value(_skey(_token_in()), data, expires_in_sec=SESSION_SECONDS)


def _person(data: dict, i) -> str:
	people = data.get("people") or []
	i = cint(i)
	if not 0 <= i < len(people):
		raise frappe.PermissionError
	return people[i]


# ------------------------------------------------------------------ who is who


def _short_name(principal: str) -> str:
	"""First name and initial ("Sunita D."), enough to tell people on one phone apart."""
	full = (frappe.get_doc("Anumati Data Principal", principal).get_password("full_name", raise_exception=False) or "").split()
	if not full:
		return frappe.db.get_value("Anumati Data Principal", principal, "principal_ref")
	return full[0] + (f" {full[-1][0]}." if len(full) > 1 else "")


def _birth_year(principal: str) -> int | None:
	row = frappe.db.get_value("Anumati Data Principal", principal, ["birth_year", "date_of_birth"], as_dict=True)
	return cint(row.birth_year) or (getdate(row.date_of_birth).year if row.date_of_birth else None)


def _decides_for_self(row) -> bool:
	return not ((row.is_minor and not row.renewal_due) or row.pwd_guarded)


def _scope(me: str) -> dict:
	"""The person and everyone they are guardian for (their latest Guardian Link to each)."""
	people, relation, links = [me], {me: "self"}, {}
	for link in frappe.get_all("Anumati Guardian Link", {"guardian": me}, ["name", "principal"], order_by="creation desc"):
		if link.principal in links or link.principal == me:
			continue
		ward = frappe.db.get_value("Anumati Data Principal", link.principal, ["is_minor", "renewal_due", "pwd_guarded", "merged_into"],
		                           as_dict=True)
		if not ward or ward.merged_into or _decides_for_self(ward):
			continue  # a child who turned 18 decides for themselves now
		links[link.principal] = link.name
		people.append(link.principal)
		relation[link.principal] = "child" if ward.is_minor else "guarded"
	return {"self": me, "people": people, "relation": relation, "links": links}


def _home(data: dict) -> dict:
	if data.get("choose"):
		return {"signed_in": True, "mode": data["mode"],
		        "choose": [{"i": i, "name": _short_name(p)} for i, p in enumerate(data["choose"])]}
	return {"signed_in": True, "mode": data["mode"],
	        "people": [{"i": i, "name": _short_name(p), "relation": data["relation"][p]}
	                   for i, p in enumerate(data.get("people") or [])]}


# ------------------------------------------------------------------ sign in


def _otp_key(phone_hash: str) -> str:
	return f"anumati:ss:otp:{phone_hash}"


def _code_hash(phone_hash: str, code: str) -> str:
	return hashlib.sha256(f"{phone_hash}:{code}".encode()).hexdigest()


def _send_code(digits: str, phone_hash: str, code: str) -> bool:
	provider = channels.provider_for("SMS")
	template = channels.template_for("otp", "sms", frappe.local.lang)
	adapter = frappe.get_module(channels.PROVIDERS.get(provider.provider, "anumati.channels.msg91"))
	status = "Sent"
	try:
		adapter.send(provider, digits, template, {"otp": code})
	except Exception:
		status = "Error"
		frappe.log_error(title="Anumati self-service code not sent", message=f"provider={provider.name}")
	channels.log(provider, "Sent", frappe.render_template(template.body, {"otp": "******"}, restrict_globals=True), phone_hash,  # staff-written SMS template, globals restricted; nosemgrep
	             template=template.name, status=status)
	return status == "Sent"


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=600)
def start(phone: str | int):
	"""Text a sign-in code. The answer is the same whether or not we know the number, so the page can't be
	used to find out who is a beneficiary; a code is only sent to a number we hold."""
	digits = pii.normalise_phone(phone)
	if len(digits) != 10:
		frappe.throw(_("Enter your 10-digit mobile number."))
	if not channels.can_send_codes(frappe.local.lang):
		return {"sent": False, "reason": "not_set_up"}
	phone_hash = pii.phone_hash(digits)
	sends = f"anumati:ss:sends:{phone_hash}"
	count = cint(_get(sends))
	if count >= MAX_SENDS:
		frappe.throw(_("Too many codes for this number. Please try again in 10 minutes."))
	frappe.cache.set_value(sends, count + 1, expires_in_sec=CODE_SECONDS)
	if inbox.principals_for_phone_hash(phone_hash):
		code = f"{secrets.randbelow(10**6):06d}"
		if _send_code(digits, phone_hash, code):
			frappe.cache.set_value(_otp_key(phone_hash), {"hash": _code_hash(phone_hash, code), "tries": 0},
			                       expires_in_sec=CODE_SECONDS)
	return {"sent": True, "to": mask_phone(digits), "expires_in": CODE_SECONDS}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=600)
def verify(phone: str | int, code: str | int):
	phone_hash = pii.phone_hash(pii.normalise_phone(phone))
	stored = _get(_otp_key(phone_hash)) if phone_hash else None
	if not stored:
		frappe.throw(_("This code has expired. Ask for a new one."))
	if stored["tries"] >= MAX_TRIES:
		frappe.cache.delete_value(_otp_key(phone_hash))
		frappe.throw(_("Too many wrong codes. Ask for a new one."))
	if not hmac.compare_digest(stored["hash"], _code_hash(phone_hash, str(code or "").strip())):
		stored["tries"] += 1
		frappe.cache.set_value(_otp_key(phone_hash), stored, expires_in_sec=CODE_SECONDS)
		return {"signed_in": False, "tries_left": MAX_TRIES - stored["tries"]}
	frappe.cache.delete_value(_otp_key(phone_hash))
	rows = frappe.get_all("Anumati Data Principal", {"phone_hash": phone_hash, "merged_into": ("is", "not set")},
	                      ["name", "is_minor", "renewal_due", "pwd_guarded"], order_by="creation asc")
	adults = [r.name for r in rows if _decides_for_self(r)]
	data = {"mode": "otp", "phone_hash": phone_hash}
	if len(adults) == 1:
		data.update(_scope(adults[0]))
	elif adults:
		data["choose"] = adults
	else:
		data["people"], data["relation"] = [], {}
	_new_session(data)
	return _home(data)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=600)
def choose(i: int | str, year: int | str):
	"""Several adults share this number: the person picks their name and confirms their year of birth."""
	data = _session()
	candidates = data.get("choose") or []
	i = cint(i)
	if not 0 <= i < len(candidates):
		raise frappe.PermissionError
	data["choose_tries"] = cint(data.get("choose_tries")) + 1
	if data["choose_tries"] > MAX_TRIES:
		frappe.cache.delete_value(_skey(_token_in()))
		raise SignInError(_("Too many tries. Please sign in again."))
	_save(data)
	known = _birth_year(candidates[i])
	if not known:
		frappe.throw(_("We don't have your year of birth, so we can't confirm it's you here. Please ask a field worker."))
	if cint(year) != known:
		frappe.throw(_("That year of birth doesn't match. Please try again."))
	data.pop("choose", None)
	data.update(_scope(candidates[i]))
	_save(data)
	return _home(data)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=600)
def code_login(code: str | int, year: int | str):
	"""Sign in with a receipt code and year of birth (for people without a phone). Can only turn uses off,
	leave, and ask us things."""
	code = (code or "").strip().upper()
	tries = f"anumati:ss:codetries:{hashlib.sha256(code.encode()).hexdigest()}"
	if cint(_get(tries)) >= MAX_TRIES:
		frappe.throw(_("Too many tries with this code. Please try again in an hour or ask a field worker."))
	principal = inbox.principal_for_short_code(code)
	if not principal or not cint(year) or _birth_year(principal) != cint(year):
		frappe.cache.set_value(tries, cint(_get(tries)) + 1, expires_in_sec=3600)
		frappe.throw(_("We couldn't find that receipt code with that year of birth."))
	data = {"mode": "code", "phone_hash": None, "self": principal, "people": [principal],
	        "relation": {principal: "self"}, "links": {}}
	_new_session(data)
	return _home(data)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def sign_out():
	token = _token_in()
	if token:
		frappe.cache.delete_value(_skey(token))
	if getattr(frappe.local, "cookie_manager", None):
		frappe.local.cookie_manager.delete_cookie(COOKIE)
	frappe.flags.anumati_ss = None
	return {"signed_in": False}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=120, seconds=60)
def home():
	"""Who is signed in (for a page reload)."""
	try:
		return _home(_session())
	except SignInError:
		return {"signed_in": False}


# ------------------------------------------------------------------ choices, history, requests


def _titles(programme: str) -> dict:
	"""Use names in the page's language, from the live notice's reviewed translation; else the base text."""
	notice = frappe.db.get_value("Anumati Notice Template", {"programme": programme, "docstatus": 1}, "name",
	                             order_by="creation desc")
	if not notice or not frappe.local.lang:
		return {}
	translation = frappe.db.get_value("Anumati Notice Translation", {"notice": notice, "language": frappe.local.lang,
	                                                         "reviewer": ("is", "set")})
	if not translation:
		return {}
	rows = frappe.get_all("Anumati Notice Purpose Translation", {"parent": translation, "parenttype": "Anumati Notice Translation"},
	                      ["purpose", "purpose_title", "description"])
	return {r.purpose: r for r in rows if r.purpose_title}


def _can_turn_on(data: dict, person: str) -> tuple[bool, str | None]:
	if data["mode"] != "otp":
		return False, _("To turn a use on, sign in with your phone number or ask a field worker.")
	row = frappe.db.get_value("Anumati Data Principal", person, ["needs_assistance", "renewal_due"], as_dict=True)
	if data["relation"].get(person) == "self" and (row.needs_assistance or row.renewal_due):
		return False, _("To turn a use on, please ask a field worker.")
	return True, None


def _programmes(data: dict, person: str) -> list[dict]:
	states = enforcement.states_for(person)
	can_on, why = _can_turn_on(data, person)
	minor = frappe.db.get_value("Anumati Data Principal", person, "is_minor")
	out = []
	for programme in sorted(set(frappe.get_all("Anumati Consent State", {"principal": person}, pluck="programme"))):
		titles = _titles(programme)
		uses = []
		for p in frappe.get_all("Anumati Purpose", {"programme": programme},
		                        ["name", "code", "purpose_title", "description", "essential", "child_allowed"],
		                        order_by="essential desc, creation asc"):
			status = (states.get(p.name) or {}).get("status") or "not_asked"
			if minor and not p.child_allowed and status != "granted":
				continue
			t = titles.get(p.name) or {}
			uses.append({"code": p.code, "title": t.get("purpose_title") or p.purpose_title,
			             "description": t.get("description") or p.description or "", "essential": p.essential,
			             "status": status})
		left = any(u["essential"] and u["status"] != "granted" for u in uses)
		out.append({
			"programme": programme, "name": frappe.db.get_value("Anumati Programme", programme, "programme_name"),
			"uses": uses, "left": left, "can_turn_on": can_on and not left, "why_not": why,
			"since": frappe.db.get_value("Anumati Consent Event", {"principal": person, "programme": programme, "action": "grant"},
			                             "server_time", order_by="creation asc"),
			"code": frappe.db.get_value("Anumati Consent Event", {"principal": person, "programme": programme}, "short_code",
			                            order_by="creation desc"),
		})
	return out


# How a decision reached us, in plain words (translated when shown).
HOW = {"app": "Field worker", "field_worker": "Field worker", "slip": "Paper slip", "sms": "SMS",
       "missed_call": "Missed call", "web": "This page", "ivr": "Phone call", "whatsapp": "WhatsApp",
       "email": "Email", "community": "Community meeting", "api": "Partner system", "hosted_page": "Website",
       "connector": "Partner system"}


def _history(person: str) -> list[dict]:
	import json

	out = []
	for e in frappe.get_all("Anumati Consent Event", {"principal": person},
	                        ["name", "short_code", "action", "programme", "channel", "server_time",
	                         "purposes_granted", "purposes_denied"], order_by="creation desc", limit=100):
		granted, denied = json.loads(e.purposes_granted or "[]"), json.loads(e.purposes_denied or "[]")
		titles = dict(frappe.get_all("Anumati Purpose", {"programme": e.programme, "code": ("in", granted + denied or ["-"])},
		                             ["code", "purpose_title"], as_list=True))
		named = lambda codes, t=titles: [t.get(c, c) for c in codes]  # noqa: E731
		withdrawn = e.action == "withdraw"
		out.append({"id": e.name, "code": e.short_code, "action": e.action, "at": str(e.server_time),
		            "programme": frappe.db.get_value("Anumati Programme", e.programme, "programme_name"),
		            "agreed": [] if withdrawn else named(granted),
		            "said_no": [] if withdrawn else named(denied),
		            "stopped": named(denied) if withdrawn else [],
		            "how": _(HOW.get(e.channel, e.channel or ""))})
	return out


def _requests(person: str) -> list[dict]:
	"""Rights / support requests and grievances, newest first, each with its conversation."""
	out = []
	for r in frappe.get_all("Anumati Rights Request", {"matched_principal": person},
	                        ["name", "request_type", "status", "received_on", "sla_due", "linked_event", "creation"],
	                        order_by="creation desc", limit=50):
		if r.request_type == "withdrawal" and r.linked_event:
			continue  # done at once (field app or My choices); it is in the history
		out.append({"id": r.name, "kind": "request", "type": r.request_type, "status": r.status,
		            "received_on": str(r.received_on), "reply_by": str(r.sla_due or ""), "_at": r.creation,
		            "messages": conversation.thread("Anumati Rights Request", r.name)})
	for g in frappe.get_all("Anumati Grievance", {"matched_principal": person},
	                        ["name", "category", "status", "received_on", "sla_due", "outcome", "person_says",
	                         "answered_on", "dpo_since", "about_request", "creation"],
	                        order_by="creation desc", limit=50):
		doc = frappe._dict(g)
		out.append({"id": g.name, "kind": "grievance", "type": g.category, "status": g.status,
		            "received_on": str(g.received_on), "reply_by": str(g.sla_due or ""), "_at": g.creation,
		            "about": g.about_request, "with_dpo": bool(g.dpo_since),
		            "outcome": _(grievance.OUTCOME_FOR_PERSON[g.outcome]) if g.outcome else None,
		            "person_says": g.person_says, "can_respond": g.status == inbox.ANSWERED,
		            "can_say_not_happy": bool(grievance.can_say_not_happy(doc)),
		            "board_route": bool(g.answered_on),
		            "messages": conversation.thread("Anumati Grievance", g.name)})
	out.sort(key=lambda r: r.pop("_at"), reverse=True)
	return out


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=120, seconds=60)
def overview(i: int | str):
	return _overview(_session(), i)


def _overview(data, i) -> dict:
	person = _person(data, i)
	return {"name": _short_name(person), "relation": data["relation"][person], "mode": data["mode"],
	        "programmes": _programmes(data, person), "history": _history(person), "requests": _requests(person)}


def _closed_request(person, raised_by, artefact, note):
	"""Every withdrawal is listed in the inbox, done; as for withdrawals in the field app."""
	frappe.get_doc({
		"doctype": "Anumati Rights Request", "request_type": "withdrawal", "channel": "web", "status": inbox.CLOSED,
		"matched_principal": person, "raised_by_role": raised_by, "linked_event": artefact["consent_id"],
		"resolution": note + " " + _("Consent event {0} ({1}).").format(artefact["consent_id"], artefact["short_code"]),
	}).insert(ignore_permissions=True)


def _raised_by(data, person):
	return "by_self" if data["relation"].get(person) == "self" else "by_guardian"


def _programme_of(person: str, programme: str):
	if not frappe.db.exists("Anumati Consent State", {"principal": person, "programme": programme}):
		raise frappe.PermissionError


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=60)
def save_choices(i: int | str, programme: str, turn_on: list | str | None = None, turn_off: list | str | None = None):
	"""Turn uses on or off in one programme. Off: a withdrawal event (essential uses stop only by leaving).
	On: a grant event, confirmed by the SMS code they signed in with."""
	data = _session()
	person = _person(data, i)
	_programme_of(person, programme)
	turn_on = [c for c in frappe.parse_json(turn_on or "[]") if isinstance(c, str)]
	turn_off = [c for c in frappe.parse_json(turn_off or "[]") if isinstance(c, str)]
	if not turn_on and not turn_off:
		frappe.throw(_("Nothing changed."))
	purposes = {p.code: p for p in frappe.get_all("Anumati Purpose", {"programme": programme}, ["name", "code", "essential"])}
	states = enforcement.states_for(person)
	for code in turn_on + turn_off:
		if code not in purposes:
			frappe.throw(_("Unknown use"))
		if purposes[code].essential:
			frappe.throw(_("A use needed for the service can only stop if you leave the programme."))
	turn_off = [c for c in turn_off if (states.get(purposes[c].name) or {}).get("status") == "granted"]
	turn_on = [c for c in turn_on if (states.get(purposes[c].name) or {}).get("status") != "granted"]
	done = []
	if turn_on:
		can, why = _can_turn_on(data, person)
		if not can:
			frappe.throw(why)
		if any((states.get(p.name) or {}).get("status") != "granted" for p in purposes.values() if p.essential):
			frappe.throw(_("You have left this programme. To rejoin, please ask a field worker."))
		done.append(_grant(data, person, programme, turn_on))
	if turn_off:
		artefact = consent.withdraw_for(person, programme, "web", str(uuid.uuid4()), turn_off,
		                                ip_address=getattr(frappe.local, "request_ip", None))
		_closed_request(person, _raised_by(data, person), artefact, _("Turned off on the self-service page."))
		done.append(artefact["short_code"])
	return {"codes": done, **_overview(data, i)}


def _grant(data, person, programme, codes) -> str:
	relation = data["relation"].get(person)
	link = (data.get("links") or {}).get(person)
	event = frappe._dict(guardian_link=link, verification_method="server_otp")
	try:
		consent._check_purposes(programme, person, codes, [])
		consent._check_who(person, "grant", event)
	except consent.ConsentRequestError:
		frappe.throw(_("This can't be turned on here. Please ask a field worker."))
	notice = frappe.db.get_value("Anumati Notice Template", {"programme": programme, "docstatus": 1},
	                             ["name", "version"], as_dict=True, order_by="creation desc")
	doc = frappe.get_doc({
		"doctype": "Anumati Consent Event", "event_uuid": str(uuid.uuid4()), "action": "grant", "principal": person,
		"programme": programme, "purposes_granted": codes, "purposes_denied": [],
		"capture_mode": GUARDIAN_MODES.get(relation, "self_digital"), "channel": "web",
		"guardian_link": link, "verification_method": "server_otp", "verification_status": "confirmed",
		"notice": notice.name if notice else None, "notice_version": notice.version if notice else None,
		"language": frappe.local.lang if frappe.db.exists("Language", frappe.local.lang or "") else None,
		"notice_delivery": "read_on_screen", "ip_address": getattr(frappe.local, "request_ip", None), "captured_by": frappe.session.user,
	})
	doc.flags.ignore_permissions = True
	doc.flags.anumati_trusted = True  # checked above; signed in with an SMS code, so confirmed
	doc.insert()
	# The SMS code they signed in with is the confirmation: keep it with the consent, as for a field consent.
	frappe.get_doc({"doctype": "Anumati Verification Attempt", "consent_event": doc.name, "verification_method": "server_otp",
	                "channel": "sms", "sent_at": now_datetime(), "delivered_at": now_datetime(), "result": "confirmed",
	                "response": _("Signed in to the self-service page with an SMS code")}).insert(ignore_permissions=True)
	return consent._artefact(doc)["short_code"]


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=60)
def leave(i: int | str, programme: str, confirm: bool | int | str = 0):
	"""Leave a programme: every use stops, essential ones too (as Record withdrawal > Leave the programme)."""
	data = _session()
	person = _person(data, i)
	_programme_of(person, programme)
	if not cint(confirm):
		frappe.throw(_("Tick that you understand first."))
	artefact = consent.withdraw_for(person, programme, "web", str(uuid.uuid4()), leave=True,
	                                ip_address=getattr(frappe.local, "request_ip", None))
	_closed_request(person, _raised_by(data, person), artefact, _("Left the programme on the self-service page."))
	return {"code": artefact["short_code"], **_overview(data, i)}


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=30, seconds=60)
def receipt(i: int | str, event: str):
	"""The receipt for one of the person's consent events, as a PDF (the Consent Receipt print format)."""
	data = _session()
	person = _person(data, i)
	if frappe.db.get_value("Anumati Consent Event", event, "principal") != person:
		raise frappe.PermissionError
	frappe.local.response.filename = f"{frappe.db.get_value('Anumati Consent Event', event, 'short_code')}.pdf"
	frappe.local.response.filecontent = receipt_file(event, as_pdf=True)
	frappe.local.response.type = "pdf"


def receipt_file(event: str, as_pdf=True):
	frappe.flags.ignore_print_permissions = True
	try:
		return frappe.get_print("Anumati Consent Event", event, "Consent Receipt", as_pdf=as_pdf, no_letterhead=1)
	finally:
		frappe.flags.ignore_print_permissions = False


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=600)
def ask(i: int | str, request_type: str, details: str | None = None):
	"""A rights / support request: see, correct or delete my data, or name someone. (Stopping a use is done
	on My choices, at once.)"""
	data = _session()
	person = _person(data, i)
	if request_type not in RIGHTS:
		frappe.throw(_("Choose what you are asking for."))
	details = (details or "").strip()
	if len(details) > conversation.MAX_LENGTH:
		frappe.throw(_("Please keep it under {0} characters.").format(conversation.MAX_LENGTH))
	doc = frappe.get_doc({
		"doctype": "Anumati Rights Request", "request_type": request_type, "channel": "web", "matched_principal": person,
		"raised_by_role": _raised_by(data, person), "sender_hash": data.get("phone_hash"),
		"received_on": now_datetime(),
	})
	doc.insert(ignore_permissions=True)
	if details:
		conversation.person_message(doc, details, data.get("phone_hash"))
	channels.send_sms(person, "rights_update", {"code": doc.name, "date": frappe.utils.formatdate(doc.sla_due),
	                                            "link": frappe.utils.get_url(conversation.PAGE)},
	                  link=("Anumati Rights Request", doc.name))
	return {"request": doc.name, "reply_by": str(doc.sla_due), **_overview(data, i)}


def _own(person: str, name: str):
	"""One of the person's own requests or grievances, by its number."""
	doctype = "Anumati Grievance" if str(name).startswith("GR-") else "Anumati Rights Request"
	if not name or frappe.db.get_value(doctype, name, "matched_principal") != person:
		raise frappe.PermissionError
	return frappe.get_doc(doctype, name)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=600)
def write(i: int | str, request: str, text: str):
	"""Write to us on one of the person's requests or grievances."""
	data = _session()
	person = _person(data, i)
	doc = _own(person, request)
	if doc.status in (inbox.CLOSED, inbox.CANNOT):
		frappe.throw(_("This is closed."))
	conversation.person_message(doc, text, data.get("phone_hash"))
	return _overview(data, i)


PHOTO_TYPES = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png", b"%PDF": "pdf"}
PHOTO_MAX = 3 * 1024 * 1024


def _read_photo(photo: str) -> tuple[bytes, str]:
	"""A photo or PDF the person added (a data URL from the page): only JPEG, PNG or PDF up to 3 MB, judged by
	its first bytes, not its name."""
	import base64

	try:
		content = base64.b64decode(photo.split(",", 1)[-1], validate=True)
	except Exception:
		frappe.throw(_("That file could not be read."))
	kind = next((ext for magic, ext in PHOTO_TYPES.items() if content.startswith(magic)), None)
	if not kind or len(content) > PHOTO_MAX:
		frappe.throw(_("Add a photo (JPG or PNG) or a PDF of up to 3 MB."))
	return content, kind


def _attach_photo(doc, content: bytes, kind: str):
	"""Kept private and encrypted on disk like consent evidence (evidence.py)."""
	file = frappe.get_doc({"doctype": "File", "file_name": f"{doc.name}-evidence.{kind}", "content": content,
	                       "is_private": 1, "attached_to_doctype": "Anumati Grievance", "attached_to_name": doc.name,
	                       "attached_to_field": "evidence"})
	file.insert(ignore_permissions=True)
	frappe.db.set_value("Anumati Grievance", doc.name, "evidence", file.file_url)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=600)
def complain(i: int | str, category: str, details: str | None = None, about_request: str | None = None, photo: str | None = None):
	"""A grievance: something went wrong with the person's data or a request."""
	data = _session()
	person = _person(data, i)
	meta = frappe.get_meta("Anumati Grievance").get_field("category").options.split("\n")
	if category not in meta:
		frappe.throw(_("Choose what it is about."))
	details = (details or "").strip()
	if not details:
		frappe.throw(_("Tell us what happened."))
	if len(details) > conversation.MAX_LENGTH:
		frappe.throw(_("Please keep it under {0} characters.").format(conversation.MAX_LENGTH))
	if about_request:
		_own(person, about_request)
	elif category == "request_not_answered":
		frappe.throw(_("Choose which request was not answered."))
	upload = _read_photo(photo) if photo else None
	doc = grievance.create(category, "web", person, raised_by_role=_raised_by(data, person),
	                       sender_hash=data.get("phone_hash"), about_request=about_request or None)
	conversation.person_message(doc, details, data.get("phone_hash"))
	if upload:
		_attach_photo(doc, *upload)
	channels.send_sms(person, "grievance_received", {"code": doc.name, "date": frappe.utils.formatdate(doc.sla_due),
	                                                 "link": frappe.utils.get_url(conversation.PAGE)},
	                  link=("Anumati Grievance", doc.name))
	return {"grievance": doc.name, "reply_by": str(doc.sla_due), **_overview(data, i)}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=600)
def respond(i: int | str, grievance_name: str, solved: bool | int | str):
	"""Did the answer solve it? Yes closes it; No (once) sends it back to the DPO."""
	data = _session()
	person = _person(data, i)
	doc = _own(person, grievance_name)
	if doc.doctype != "Anumati Grievance":
		raise frappe.PermissionError
	grievance.respond(doc, bool(cint(solved)))
	return _overview(data, i)
