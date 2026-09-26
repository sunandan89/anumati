// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

frappe.ui.form.on("Notice Template", {
	setup(frm) {
		// Only offer purposes and processors that belong to this notice's programme.
		frm.set_query("purpose", "purposes", () => ({ filters: { programme: frm.doc.programme } }));
		frm.set_query("purpose", "processors", () => ({ filters: { programme: frm.doc.programme } }));
	},
});
