// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

frappe.ui.form.on("Data Principal", {
	refresh(frm) {
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
