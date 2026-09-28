// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE
//
// A translation (and its audio) is only served once a named reviewer signs off (spec A1, T13).

frappe.ui.form.on("Notice Translation", {
	refresh(frm) {
		if (!frm.doc.reviewer) {
			frm.set_intro(__("Not reviewed: the field app and the API will not serve this translation until a reviewer signs off."), "orange");
		} else if (frm.doc.audio_file && frm.doc.audio_machine_made && !frm.doc.audio_reviewed_by) {
			frm.set_intro(__("Audio is machine-made and not reviewed: it will not be played in the field."), "orange");
		} else {
			frm.set_intro(__("Reviewed by {0}", [frm.doc.reviewer]), "green");
		}
		anumati_notice_audio(frm);
	},
	reviewer(frm) {
		if (frm.doc.reviewer && !frm.doc.reviewed_on) frm.set_value("reviewed_on", frappe.datetime.get_today());
	},
});
