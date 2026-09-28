"""Notice API, v1: /api/v2/method/anumati.api.v1.notice.get_active"""

import frappe
from frappe import _

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
			"Purpose", row.purpose, ["code", "purpose_title", "description", "essential", "child_allowed"], as_dict=True
		)
		purposes.append(p)
	out = {
		"notice": notice.name, "version": notice.version, "programme": programme,
		"summary": notice.summary, "full_text": notice.full_text, "purposes": purposes,
		"cross_border_transfers": notice.cross_border_transfers, "pictorial_card": notice.pictorial_card,
		**{k: notice.get(k) for k in RULE3}, "translation": None,
		# Audio of the base notice, once a reviewer approved it (machine-made audio never plays unreviewed).
		"audio_file": notice.audio_file if (notice.audio_file and (not notice.audio_machine_made or notice.audio_reviewed_by)) else None,
	}
	if language:
		t = frappe.db.get_value(
			"Notice Translation", {"notice": name, "language": language},
			["summary", "full_text", "machine_translated", "reviewer", "audio_file", "audio_machine_made",
			 "audio_reviewed_by", "pictorial_card", *LABELS, *RULE3], as_dict=True,
		)
		if t and t.reviewer:
			out["translation"] = {
				"language": language, "summary": t.summary, "full_text": t.full_text,
				"audio_file": t.audio_file if (not t.audio_machine_made or t.audio_reviewed_by) else None,
				"pictorial_card": t.pictorial_card, **{k: t.get(k) for k in LABELS},
				# Translated Rule 3 contents; blank ones fall back to the notice's own text on the client.
				**{k: t.get(k) for k in RULE3 if t.get(k)},
			}
	return out
