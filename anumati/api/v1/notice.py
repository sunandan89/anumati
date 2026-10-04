"""Notice API, v1: /api/v2/method/anumati.api.v1.notice.get_active"""

import frappe
from frappe import _

from anumati import channels, profile

RULE3 = ("withdrawal_methods", "rights_text", "board_complaint_route", "dpo_contact", "security_summary")
LABELS = ("label_yes_all", "label_no_all", "label_manage", "label_save")


@frappe.whitelist(methods=["GET"])
def get_active(programme, language=None):
	"""The live notice for a programme: purposes, Rule 3 contents, and a reviewed translation if one exists.
	Machine-made translations or audio that no reviewer signed off are never served (spec A1, T13)."""
	frappe.has_permission("Notice Template", "read", throw=True)
	name = frappe.db.get_value(
		"Notice Template", {"programme": programme, "docstatus": 1, "status": "Published"},
		order_by="creation desc",
	)
	if not name:
		frappe.throw(_("Programme {0} has no published notice").format(programme), frappe.DoesNotExistError)
	notice = frappe.get_doc("Notice Template", name)
	purposes = []
	for row in notice.purposes:
		p = frappe.db.get_value(
			"Purpose", row.purpose, ["code", "purpose_title", "description", "essential", "child_allowed", "needs_phone"],
			as_dict=True,
		)
		purposes.append(p)
	out = {
		"notice": notice.name, "version": notice.version, "programme": programme,
		"summary": notice.summary, "full_text": notice.full_text, "purposes": purposes,
		"cross_border_transfers": notice.cross_border_transfers, "pictorial_card": notice.pictorial_card,
		**{k: notice.get(k) for k in RULE3}, "translation": None,
		# Audio of the base notice (woman's and man's voice), once a reviewer approved it: machine-made
		# audio never plays unreviewed.
		**_audio(notice),
		# Extra questions about the person this programme asks (none unless switched on), in the
		# requested language where translated.
		"profile_questions": profile.for_notice(programme, name, language),
		# Whether the server can text codes now; if not, the app uses the worker's phone with the voice 'haan'.
		"server_codes": channels.can_send_codes(language),
	}
	if language:
		t = frappe.db.get_value(
			"Notice Translation", {"notice": name, "language": language},
			["name", "summary", "full_text", "machine_translated", "reviewer", "audio_file", "audio_file_male", "audio_machine_made",
			 "audio_reviewed_by", "pictorial_card", *LABELS, *RULE3], as_dict=True,
		)
		if t and t.reviewer:
			out["translation"] = {
				"language": language, "summary": t.summary, "full_text": t.full_text,
				**_audio(t),
				"pictorial_card": t.pictorial_card, **{k: t.get(k) for k in LABELS},
				# Translated Rule 3 contents; blank ones fall back to the notice's own text on the client.
				**{k: t.get(k) for k in RULE3 if t.get(k)},
				# Translated names of the uses; a use left out shows its own (base) text.
				"purposes": _purpose_labels(t.name),
			}
	return out


def _audio(doc) -> dict:
	approved = not doc.get("audio_machine_made") or doc.get("audio_reviewed_by")
	out = {k: (doc.get(k) if approved else None) for k in ("audio_file", "audio_file_male")}
	# Lets the phone credit the voice (Sarvam AI) under a machine-made recording.
	out["audio_machine_made"] = 1 if approved and doc.get("audio_machine_made") and doc.get("audio_file") else 0
	return out


def _purpose_labels(translation: str) -> list[dict]:
	rows = frappe.get_all("Notice Purpose Translation", {"parent": translation, "parenttype": "Notice Translation"},
	                      ["purpose", "purpose_title", "description"], order_by="idx asc")
	codes = dict(frappe.get_all("Purpose", {"name": ("in", [r.purpose for r in rows] or ["-"])}, ["name", "code"],
	                            as_list=True))
	return [{"code": codes.get(r.purpose), "purpose_title": r.purpose_title, "description": r.description}
	        for r in rows if codes.get(r.purpose) and (r.purpose_title or r.description)]
