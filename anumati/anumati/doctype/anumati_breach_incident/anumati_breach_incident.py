# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

from anumati import breach, channels, pii

SAMPLE_CODE = "AN-XXXXXX"


class AnumatiBreachIncident(Document):
	def validate(self):
		# Lost-phone incidents tell the people whose data was on that phone, unless the DPO picks otherwise.
		if not self.notify_audience and self.breach_type == "lost_device" and self.field_device:
			self.notify_audience = "lost_phone"
		for row in self.visit_list or []:
			if row.told and not row.told_on:
				row.told_on = frappe.utils.today()


def _values(values):
	values = json.loads(values) if isinstance(values, str) else (values or {})
	return {k: values[k] for k in ("notify_audience", "notify_ids", "field_device", "programme") if k in values}


@frappe.whitelist(methods=["POST"])
def summary(name: str, values: dict | str | None = None):
	"""Counts, preview and readiness for the Tell affected people tab. Counts and texts only: no names, no numbers."""
	doc = frappe.get_doc("Anumati Breach Incident", name)
	doc.check_permission("read")
	unsaved = json.loads(values) if isinstance(values, str) else (values or {})
	for field in ("what_happened_en", "what_happened_hi", "can_do_en", "can_do_hi"):
		if field in unsaved:
			doc.set(field, unsaved[field])
	rows = breach.plan(doc, _values(values))
	counts = breach.counts(rows)
	languages = sorted(counts["languages"]) or ["en"]
	ready, reason = breach.readiness(doc, languages)
	previews, parts = [], 0
	for lang in languages:
		template = breach.any_template(lang)
		text = frappe.render_template(template.body, breach.context(doc, lang, SAMPLE_CODE), restrict_globals=True) if template else ""  # staff-written SMS template, globals restricted; nosemgrep
		people = counts["languages"].get(lang, 0)
		n = breach.sms_parts(text) if text else 0
		parts += n * sum(1 for r in rows if r["language"] == lang and r["route"] != "none")
		previews.append({"language": lang, "people": people, "text": text, "parts": n,
		                 "approved": bool(template and template.approved and template.language == lang)})
	return {
		"counts": counts, "previews": previews, "ready": ready, "reason": reason,
		"missing": breach.blanks_missing(doc, languages),
		"estimate": {"parts": parts, "rupees": round(parts * breach.SMS_RATE)},
		"sender": (channels.provider_for("SMS") or frappe._dict()).get("provider_name"),
		"results": breach.results(doc) if doc.notify_sent_on else None,
		"can_send": bool(breach.DPO_ROLES & set(frappe.get_roles())) and doc.has_permission("write"),
	}


def _for_dpo(name):
	doc = frappe.get_doc("Anumati Breach Incident", name)
	doc.check_permission("write")
	breach.can_send_as_dpo()
	return doc


@frappe.whitelist(methods=["POST"])
def send(name: str, confirm: bool | int | str):
	"""Send the breach notice to everyone in the plan, in the background. `confirm` must equal the SMS count."""
	doc = _for_dpo(name)
	if doc.notify_sent_on:
		frappe.throw(_("The breach notice was already sent on {0}. Use Retry failed for anyone it didn't reach.").format(
			frappe.utils.format_datetime(doc.notify_sent_on)))
	rows = breach.plan(doc)
	counts = breach.counts(rows)
	if not counts["total"]:
		frappe.throw(_("Nobody matches Who to tell yet."))
	languages = sorted(counts["languages"])
	ready, reason = breach.readiness(doc, languages)
	if not ready:
		frappe.throw(_("Sending SMS is off: {0}").format(reason))
	missing = breach.blanks_missing(doc, languages)
	if missing:
		frappe.throw(_("Fill in: {0}").format(", ".join(missing)))
	if cint(confirm) != counts["sms"]:
		frappe.throw(_("Type {0} to confirm.").format(counts["sms"]))
	# Claim the send before queuing, so a second click or a second DPO can't send it twice.
	doc.db_set({"notify_sent_on": now_datetime(), "notify_sent_by": frappe.session.user})
	frappe.enqueue("anumati.breach.send_all", queue="long", timeout=3600, incident=doc.name,
	               user=frappe.session.user, now=frappe.flags.in_test, enqueue_after_commit=not frappe.flags.in_test)
	return {"queued": counts["sms"], "visit": counts["no_phone"]}


@frappe.whitelist(methods=["POST"])
def send_test(name: str):
	"""Send the notice to the signed-in DPO's own mobile (from their user profile), in each language used."""
	doc = _for_dpo(name)
	mobile = frappe.db.get_value("User", frappe.session.user, "mobile_no")
	if not mobile:
		frappe.throw(_("Add your mobile number to your user profile (My Settings) to get a test."))
	provider = channels.provider_for("SMS")
	languages = sorted(breach.counts(breach.plan(doc))["languages"]) or ["en"]
	ready, reason = breach.readiness(doc, languages)
	if not ready:
		frappe.throw(_("Sending SMS is off: {0}").format(reason))
	adapter = frappe.get_module(channels.PROVIDERS.get(provider.provider, "anumati.channels.msg91"))
	for lang in languages:
		template = channels.template_for(breach.EVENT, "sms", lang)
		adapter.send(provider, pii.normalise_phone(mobile), template, breach.context(doc, lang, SAMPLE_CODE))
	from anumati.api.v1.principal import mask_phone

	return {"to": mask_phone(mobile), "languages": languages}


@frappe.whitelist(methods=["POST"])
def retry(name: str):
	doc = _for_dpo(name)
	if not doc.notify_sent_on:
		frappe.throw(_("Nothing has been sent yet."))
	return breach.retry_failed(doc)
