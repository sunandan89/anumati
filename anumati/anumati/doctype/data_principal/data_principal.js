// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

frappe.ui.form.on("Data Principal", {
	refresh(frm) {
		// Name and phone are encrypted fields (shown as dots). Show the name and a masked number instead;
		// each view is logged. The full number never reaches the browser.
		if (!frm.is_new()) {
			frappe.call({ method: "anumati.api.v1.principal.reveal", args: { principal: frm.doc.name }, type: "GET" }).then((r) => {
				const p = r.message || {};
				frm.dashboard.clear_headline();
				const parts = [p.full_name, p.phone_masked].filter(Boolean).map(frappe.utils.escape_html);
				if (parts.length) frm.dashboard.set_headline(`<b>${parts[0]}</b>${parts[1] ? " · " + parts[1] : ""}`);
			});
			anumati_consent_chips(frm);
		}
		if (frm.doc.merged_into) {
			frm.set_intro(__("Merged into {0}; its history now lives there.", [frm.doc.merged_into]), "blue");
		} else if (frm.doc.relationship_ended_on) {
			frm.set_intro(__("Relationship ended on {0}. Retention clocks that start at 'relationship ended' are running.",
				[frappe.datetime.str_to_user(frm.doc.relationship_ended_on)]), "orange");
		}
		if (!frm.is_new() && !frm.doc.relationship_ended_on && frm.perm[0] && frm.perm[0].write) {
			frm.add_custom_button(__("Relationship ended"), () => {
				frappe.confirm(
					__("Mark that the programme no longer serves this person? This starts retention clocks that run from 'relationship ended' (spec T16) and is recorded in the history."),
					() => frm.set_value("relationship_ended_on", frappe.datetime.get_today()).then(() => frm.save())
				);
			});
		}
	},
});

// Current consent per purpose, as coloured chips above the tabs (from Consent State, read-only).
const CHIP = { granted: "green", withdrawn: "red", refused: "gray", expired: "gray", not_asked: "gray" };

function anumati_consent_chips(frm) {
	if (!frappe.model.can_read("Consent State")) return;
	frappe.db.get_list("Consent State", {
		filters: { principal: frm.doc.name },
		fields: ["purpose", "status", "verification_status"],
		limit: 100,
	}).then((rows) => {
		if (!rows.length) return;
		const esc = frappe.utils.escape_html;
		const chips = rows.map((r) => {
			const waiting = r.status === "granted" && r.verification_status === "unconfirmed";
			const tone = waiting ? "orange" : CHIP[r.status] || "gray";
			const note = waiting ? __("waiting for confirmation") : __(r.status.replace(/_/g, " "));
			return `<span class="indicator-pill ${tone}" style="margin:0 6px 6px 0" title="${esc(note)}">${esc(r.purpose)} · ${esc(note)}</span>`;
		}).join("");
		frm.dashboard.add_section(`<div style="display:flex;flex-wrap:wrap">${chips}</div>`, __("Consent today"));
	});
}
