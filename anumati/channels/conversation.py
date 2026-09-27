"""WhatsApp and IVR menus (spec section 6, prototype › Beneficiary › WhatsApp): the same withdrawal and
rights rules as SMS, with a menu instead of keywords.

  STOP (or any message) ─► who is this for? (only when the number is shared) ─► what to stop?
      1  every optional use          2..n  just one purpose          E  delete my data    D  see my data

Menus never show names: people on a shared number are listed by receipt code and date. The Rights
Request is opened at the first message so the SLA clock starts at receipt; menu state lives in Redis
with a short TTL, keyed by the salted phone hash."""

import json

import frappe
from frappe import _
from frappe.utils import formatdate

from anumati import inbox

TTL = 15 * 60
ERASE, DATA = "E", "D"


def _key(phone_hash):
	return f"anumati:conversation:{phone_hash}"


def get_state(phone_hash):
	return frappe.cache.get_value(_key(phone_hash), expires=True) or {}


def set_state(phone_hash, state):
	frappe.cache.set_value(_key(phone_hash), state, expires_in_sec=TTL)


def clear_state(phone_hash):
	frappe.cache.delete_value(_key(phone_hash))


def open_request(channel, phone_hash, text, principal=None, request_type="withdrawal", comm=None):
	from anumati.api.v1.channel import _request

	return _request(request_type, channel, phone_hash, text, principal=principal, comm=comm)


def latest_grant(principal):
	return frappe.db.get_value("Consent Event", {"principal": principal, "action": ("in", ["grant", "renew"])},
	                           ["name", "short_code", "programme", "server_time"], order_by="chain_seq desc", as_dict=True)


def who_options(people) -> list[dict]:
	"""Choices for a shared number, by receipt code and date only."""
	out = []
	for p in people:
		grant = latest_grant(p.name)
		label = f"{grant.short_code} ({formatdate(grant.server_time)})" if grant else p.principal_ref
		out.append({"principal": p.name, "label": label})
	return out


def purpose_options(principal) -> list[dict]:
	"""Granted optional purposes, numbered from 2 (1 = all optional uses)."""
	rows = frappe.get_all("Consent State", {"principal": principal, "status": "granted"}, ["programme", "purpose"],
	                      order_by="purpose")
	out = []
	for r in rows:
		purpose = frappe.db.get_value("Purpose", r.purpose, ["code", "purpose_title", "essential"], as_dict=True)
		if purpose and not purpose.essential:
			out.append({"programme": r.programme, "code": purpose.code, "title": purpose.purpose_title or purpose.code})
	return out


def menu_text(options) -> str:
	lines = [_("What would you like to do? Reply with a number or letter:"), _("1. Stop every optional use")]
	lines += [_("{0}. Stop only: {1}").format(i, o["title"]) for i, o in enumerate(options, start=2)]
	lines += [_("E. Delete my data"), _("D. Send me what you hold about me")]
	return "\n".join(lines)


def who_text(options) -> str:
	lines = [_("This number is used by more than one person. Who is this for? Reply with a number:")]
	lines += [f"{i}. {o['label']}" for i, o in enumerate(options, start=1)]
	return "\n".join(lines)


def withdraw(principal, channel, request, purposes_by_programme: dict) -> list[str]:
	from anumati.api.v1 import consent

	codes = []
	for prog, purposes in sorted(purposes_by_programme.items()):
		art = consent.withdraw_for(principal, prog, channel, f"{channel}-{frappe.scrub(request.name)}-{prog}", purposes or None)
		codes.append(art["short_code"])
	request.reload()
	request.update({"status": "Closed", "matched_principal": principal,
	                "linked_event": frappe.db.get_value("Consent Event", {"short_code": codes[0]}) if codes else None,
	                "resolution": _("Withdrawn by {0}: {1}").format(channel, ", ".join(codes))})
	request.flags.ignore_permissions = True
	request.save()
	return codes


def _retype(request, request_type, principal):
	request.reload()
	request.update({"request_type": request_type, "matched_principal": principal})
	request.flags.ignore_permissions = True
	request.save()


def handle(channel, phone_hash, text, comm=None) -> str:
	"""One inbound message on a menu channel. Returns the reply text."""
	answer = (text or "").strip().upper()
	state = get_state(phone_hash)

	if state.get("step") == "who":
		options = state["options"]
		if answer.isdigit() and 1 <= int(answer) <= len(options):
			principal = options[int(answer) - 1]["principal"]
			return _show_menu(phone_hash, state["request"], principal)
		return who_text(options)

	if state.get("step") == "menu":
		return _choose(channel, phone_hash, state, answer)

	# A new conversation: "STOP <code>" goes straight to that person; otherwise match the number.
	words = answer.split()
	if words and words[0] in ("DATA", "HELP"):
		req = open_request(channel, phone_hash, text, request_type="access" if words[0] == "DATA" else "grievance", comm=comm)
		return _("Thank you. Your request {0} is recorded; we will reply within 30 days.").format(req.name)
	principal = None
	if len(words) > 1 and words[0] == "STOP":
		principal = inbox.event_for_short_code(words[1])[0]
	people = [frappe._dict(name=principal)] if principal else inbox.principals_for_phone_hash(phone_hash)
	req = open_request(channel, phone_hash, text, principal=people[0].name if len(people) == 1 else None, comm=comm)
	if not people:
		return _("We could not find a consent for this number. Reply STOP followed by the code on your receipt "
		         "(for example STOP AN-7K2Q9C), or tell any field worker. Your request {0} is recorded.").format(req.name)
	if len(people) == 1:
		return _show_menu(phone_hash, req.name, people[0].name)
	options = who_options(people)
	set_state(phone_hash, {"step": "who", "request": req.name, "options": options})
	return who_text(options)


def _show_menu(phone_hash, request, principal):
	options = purpose_options(principal)
	set_state(phone_hash, {"step": "menu", "request": request, "principal": principal, "options": options})
	return menu_text(options)


def _choose(channel, phone_hash, state, answer):
	request = frappe.get_doc("Rights Request", state["request"])
	principal, options = state["principal"], state["options"]
	if answer == ERASE:
		_retype(request, "erasure", principal)
		clear_state(phone_hash)
		return _("Your request to delete your data is recorded (ref {0}). It will be completed within 30 days.").format(request.name)
	if answer == DATA:
		_retype(request, "access", principal)
		clear_state(phone_hash)
		return _("Your request is recorded (ref {0}). We will send you a summary of what we hold.").format(request.name)
	if answer == "1":
		if not options:
			clear_state(phone_hash)
			return _("There is no optional use to stop. Essential services continue.")
		by_programme = {}
		for o in options:
			by_programme.setdefault(o["programme"], []).append(o["code"])
		codes = withdraw(principal, channel, request, by_programme)
		clear_state(phone_hash)
		return _("Done. Every optional use has been stopped ({0}). Essential services continue. Ref {1}.").format(
			", ".join(codes), request.name)
	if answer.isdigit() and 2 <= int(answer) <= len(options) + 1:
		o = options[int(answer) - 2]
		codes = withdraw(principal, channel, request, {o["programme"]: [o["code"]]})
		clear_state(phone_hash)
		return _("Done. {0} has been stopped ({1}). Ref {2}.").format(o["title"], ", ".join(codes), request.name)
	return menu_text(options)


# ------------------------------------------------------------------ voice (DTMF)


def ivr_prompt(phone_hash, digits=None) -> tuple[str, bool]:
	"""One step of the voice menu. Returns (what to say, whether to gather another key press).
	Voice uses the same menu and state; a key press is the reply."""
	state = get_state(phone_hash)
	if digits is None and not state:
		reply = handle("ivr", phone_hash, "STOP")
	else:
		key = {"7": ERASE, "8": DATA}.get(digits or "", digits or "")
		reply = handle("ivr", phone_hash, key)
	spoken = (reply.replace("Reply with a number or letter", "Press a key").replace("Reply with a number", "Press a key")
	          .replace("E. Delete my data", "7. Delete my data").replace("D. Send me", "8. Send me"))
	return spoken, bool(get_state(phone_hash))
