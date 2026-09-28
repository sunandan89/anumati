// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE
//
// Natural notice audio (Sarvam AI) on Notice and Notice Translation forms: make it, listen to it in full,
// approve it. The field app plays machine-made audio only after approval (server enforces this).
window.anumati_notice_audio = function (frm) {
	if (frm.is_new()) return;
	const reviewer = frappe.user.has_role(["Anumati DPO", "Anumati Admin", "System Manager"]);
	const can_make = frm.doctype === "Notice Template" ? reviewer : frm.perm[0] && frm.perm[0].write;
	const call = (method, message) =>
		frappe.call({ method, args: { doctype: frm.doctype, name: frm.doc.name }, freeze: true, freeze_message: message })
			.then(() => frm.reload_doc());

	if (can_make) {
		frm.add_custom_button(frm.doc.audio_file ? __("Make audio again") : __("Make natural audio"), () =>
			frappe.confirm(
				__("Sarvam AI will read this notice aloud twice, in the woman's and the man's voice chosen in Anumati Settings; each phone plays the one matching its field worker. Only the notice text is sent, never anyone's personal data. The audio plays in the field only after a reviewer approves it."),
				() => call("anumati.voice.generate_notice_audio", __("Making audio… this can take a minute"))
			), __("Audio"));
	}
	if (frm.doc.audio_file && frm.doc.audio_machine_made && !frm.doc.audio_reviewed_by && reviewer) {
		frm.add_custom_button(__("Approve audio"), () =>
			frappe.confirm(__("Have you listened to both recordings in full, and do they say exactly what the notice says?"),
				() => call("anumati.voice.approve_notice_audio", __("Approving…"))
			), __("Audio"));
	}
	if (frm.doc.audio_file) {
		const state = frm.doc.audio_machine_made && !frm.doc.audio_reviewed_by
			? `<span class="indicator-pill orange">${__("Machine-made, not approved: not played in the field")}</span>`
			: `<span class="indicator-pill green">${frm.doc.audio_reviewed_by ? __("Approved by {0}", [frappe.utils.escape_html(frm.doc.audio_reviewed_by)]) : __("Recorded audio")}</span>`;
		const $box = $(`<div style="display:flex;flex-direction:column;gap:8px"><div>${state}</div></div>`);
		[[frm.doc.audio_file, __("Woman's voice")], [frm.doc.audio_file_male, __("Man's voice")]].forEach(([url, label]) => {
			if (!url) return;
			const $row = $(`<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap"><span class="text-muted" style="min-width:110px">${label}</span></div>`);
			$row.append($("<audio controls preload='none' style='max-width:360px'></audio>").attr("src", url));
			$box.append($row);
		});
		frm.dashboard.add_section($box, __("Audio notice"));
	}
};
