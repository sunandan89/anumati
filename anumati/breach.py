"""Breach notification: tell the people affected by a breach (DPDP Rules: intimate each affected person, in their
language, without delay). Breach Incident › Tell affected people.

Who: people whose data was on a lost field phone, everyone in a programme, people with the affected uses, or a list
of IDs. People who withdrew or left are included: a breach notice is a legal duty, not a use of their data.
How: one SMS each through the approved breach-notice Message Template (DLT rules allow only pre-approved texts),
to their own phone or, for a child or an adult with a guardian, to the guardian's. People without a phone, and
anyone whose SMS fails, go on the field visit list (IDs only) so a field worker tells them in person.
Nothing here returns or logs a name or phone number."""

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from anumati import channels, pii

EVENT = "breach_notice"
LANGS = ("hi", "en")  # languages the DPO writes the blanks in; anyone else gets English
SMS_RATE = 0.2  # ₹ per SMS part, for the estimate only
DPO_ROLES = {"Anumati DPO", "System Manager"}


# ------------------------------------------------------------------ who


def audience(doc, values=None) -> list[str]:
	"""Data Principal names for the incident's "Who to tell" choice (values override the saved ones)."""
	v = frappe._dict({k: doc.get(k) for k in ("notify_audience", "notify_ids", "field_device", "programme")})
	v.update(values or {})
	purposes = [r.purpose for r in doc.get("purposes_affected") or []]
	if v.notify_audience == "lost_phone":
		if not v.field_device:
			return []
		names = frappe.get_all("Anumati Consent Event", {"device_id": v.field_device}, pluck="principal", distinct=True)
	elif v.notify_audience == "whole_programme":
		if not v.programme:
			return []
		names = frappe.get_all("Anumati Consent Event", {"programme": v.programme}, pluck="principal", distinct=True)
	elif v.notify_audience == "affected_uses":
		if not purposes:
			return []
		names = frappe.get_all("Anumati Consent State", {"purpose": ("in", purposes)}, pluck="principal", distinct=True)
	elif v.notify_audience == "id_list":
		refs = [line.strip() for line in (v.notify_ids or "").splitlines() if line.strip()]
		if not refs:
			return []
		names = frappe.get_all("Anumati Data Principal", {"principal_ref": ("in", refs)}, pluck="name")
	else:
		return []
	if not names:
		return []
	return frappe.get_all("Anumati Data Principal", {"name": ("in", names), "merged_into": ("is", "not set")},
	                      pluck="name", order_by="principal_ref")


def language(person) -> str:
	return person.preferred_language if person.preferred_language in LANGS else "en"


def plan(doc, values=None) -> list[dict]:
	"""One row per person: principal, principal_ref, language, route (own / guardian / none). Phones stay here."""
	rows = []
	for name in audience(doc, values):
		person = frappe.get_doc("Anumati Data Principal", name)
		own = person.get_password("phone", raise_exception=False)
		to = channels.contact_phone(person)
		route = "none" if not to else ("own" if own and pii.normalise_phone(to) == pii.normalise_phone(own) else "guardian")
		rows.append({"principal": name, "principal_ref": person.principal_ref, "language": language(person),
		             "route": route, "phone": to})
	return rows


def counts(rows) -> dict:
	by_lang = {}
	for r in rows:
		by_lang[r["language"]] = by_lang.get(r["language"], 0) + 1
	return {
		"total": len(rows),
		"sms": sum(1 for r in rows if r["route"] != "none"),
		"own": sum(1 for r in rows if r["route"] == "own"),
		"guardian": sum(1 for r in rows if r["route"] == "guardian"),
		"no_phone": sum(1 for r in rows if r["route"] == "none"),
		"languages": by_lang,
	}


# ------------------------------------------------------------------ what


def any_template(lang: str):
	"""The breach-notice template for a language, approved or not (for the preview); English if none."""
	for code in dict.fromkeys([lang, "en"]):
		name = frappe.db.get_value("Anumati Message Template", {"template_event": EVENT, "channel": "sms", "language": code},
		                           "name", order_by="approved desc")
		if name:
			return frappe.get_doc("Anumati Message Template", name)
	return None


def context(doc, lang: str, code: str | None) -> dict:
	settings = frappe.get_cached_doc("Anumati Settings")
	helpline = settings.get("helpline") or (_("tell any field worker") if lang == "en" else "किसी भी कार्यकर्ता को बताएँ")
	return {
		"org": settings.org_legal_name or "",
		"what_happened": (doc.get(f"what_happened_{lang}") or "").strip(),
		"can_do": (doc.get(f"can_do_{lang}") or "").strip(),
		"helpline": helpline,
		"code": code or "",
	}


def latest_code(principal: str, programme: str | None = None) -> str | None:
	"""The person's own latest receipt code, so they can quote it when they call."""
	filters = {"principal": principal, **({"programme": programme} if programme else {})}
	return (frappe.db.get_value("Anumati Consent Event", filters, "short_code", order_by="creation desc")
	        or frappe.db.get_value("Anumati Consent Event", {"principal": principal}, "short_code", order_by="creation desc"))


def sms_parts(text: str) -> int:
	"""SMS parts: 160/153 characters for plain text, 70/67 once any character is outside GSM (e.g. Hindi)."""
	unicode = any(ord(ch) > 127 for ch in text)
	single, multi = (70, 67) if unicode else (160, 153)
	return 1 if len(text) <= single else -(-len(text) // multi)


def blanks_missing(doc, languages) -> list[str]:
	missing = []
	for lang in languages:
		for field in ("what_happened", "can_do"):
			if not (doc.get(f"{field}_{lang}") or "").strip():
				missing.append(doc.meta.get_label(f"{field}_{lang}"))
	return missing


def readiness(doc, languages) -> tuple[bool, str]:
	"""Whether real SMS can go out now, and if not, why (shown as the yellow note)."""
	provider = channels.provider_for("SMS")
	if not provider or not (provider.get_password("api_key", raise_exception=False) or frappe.conf.get("msg91_auth_key")):
		return False, _("no SMS account is set up yet (Setup › Channel Provider with an MSG91 key).")
	if not all(channels.template_for(EVENT, "sms", lang) for lang in (languages or ["en"])):
		return False, _("no approved breach-notice template yet. Ask the MSG91 account owner to register the Hindi and "
		                "English breach notice for DLT approval, then mark it approved under Setup › Message Template.")
	return True, ""


# ------------------------------------------------------------------ send


def can_send_as_dpo():
	if not DPO_ROLES & set(frappe.get_roles()):
		frappe.throw(_("Only the DPO can send breach notices."), frappe.PermissionError)


def send_one(doc, row, provider) -> tuple[str, str | None]:
	"""Send one breach notice. Returns (outcome, Communication name); outcome is sent / failed / none."""
	if row["route"] == "none":
		return "none", None
	template = channels.template_for(EVENT, "sms", row["language"]) or channels.template_for(EVENT, "sms", "en")
	lang = template.language if template.language in LANGS else "en"
	ctx = context(doc, lang, latest_code(row["principal"], doc.programme))
	body = frappe.render_template(template.body, ctx, restrict_globals=True)  # staff-written SMS template, globals restricted; nosemgrep
	adapter = frappe.get_module(channels.PROVIDERS.get(provider.provider, "anumati.channels.msg91"))
	outcome, message_id = "sent", None
	try:
		message_id = adapter.send(provider, pii.normalise_phone(row["phone"]), template, ctx)
	except Exception:
		outcome = "failed"
		frappe.log_error(title="Anumati breach notice send failed", message=f"incident={doc.name} template={template.name}")
	comm = channels.log(provider, "Sent", body, pii.phone_hash(row["phone"]), template=template.name,
	                    status="Sent" if outcome == "sent" else "Error", message_id=message_id,
	                    link=("Anumati Breach Incident", doc.name), delivery=f"sms_{outcome}")
	return outcome, comm


def send_all(incident: str, user: str):
	"""Background job: send to everyone in the plan, fill the field visit list and the 72-hour steps."""
	doc = frappe.get_doc("Anumati Breach Incident", incident)
	provider = channels.provider_for("SMS")
	sent = failed = 0
	for row in plan(doc):
		outcome, _comm = send_one(doc, row, provider)
		if outcome == "sent":
			sent += 1
			continue
		failed += outcome == "failed"
		doc.append("visit_list", {"principal": row["principal"], "principal_ref": row["principal_ref"],
		                          "language": row["language"], "reason": "no_phone" if outcome == "none" else "sms_failed"})
	doc.notify_sent = sent + failed
	doc.notify_failed = failed
	doc.notify_delivered = 0
	doc.notifications_sent = cint(doc.notifications_sent) + sent
	doc.principals_notified_on = doc.principals_notified_on or now_datetime()
	if doc.status in ("Assessing", "Contained"):
		doc.status = "Notifying"
	doc.flags.ignore_permissions = True
	doc.save()
	doc.add_comment("Info", _("Breach notice sent by SMS to {0} people ({1} failed); {2} on the field visit list.").format(
		sent, failed, len(doc.visit_list)))
	frappe.publish_realtime("anumati_breach_sent", {"incident": incident}, user=user, after_commit=True)


def retry_failed(doc) -> dict:
	"""Send again to the people whose SMS failed and who haven't been told in person yet."""
	provider = channels.provider_for("SMS")
	plans = {r["principal"]: r for r in plan(doc)}
	retried = ok = 0
	for row in list(doc.visit_list):
		if row.reason != "sms_failed" or row.told or row.principal not in plans:
			continue
		retried += 1
		outcome, _comm = send_one(doc, plans[row.principal], provider)
		if outcome == "sent":
			ok += 1
			doc.remove(row)
	doc.notify_failed = max(cint(doc.notify_failed) - ok, 0)
	doc.notifications_sent = cint(doc.notifications_sent) + ok
	doc.flags.ignore_permissions = True
	doc.save()
	return {"retried": retried, "sent": ok}


def results(doc) -> dict:
	"""Delivered / failed / waiting from the delivery reports, counting each person's latest message once (a retry
	that got through replaces the failed one). People are told apart by the salted phone hash, never the number."""
	rows = frappe.get_all("Communication", {"reference_doctype": "Anumati Breach Incident", "reference_name": doc.name},
	                      ["anumati_sender_hash", "anumati_delivery"], order_by="creation asc")
	latest = {}
	for r in rows:
		latest[r.anumati_sender_hash] = r.anumati_delivery
	states = list(latest.values())
	delivered = states.count("sms_delivered")
	failed = states.count("sms_failed")
	return {"sent": len(states), "delivered": delivered, "failed": failed, "waiting": len(states) - delivered - failed}
