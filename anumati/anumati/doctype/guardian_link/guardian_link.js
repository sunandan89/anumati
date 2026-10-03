// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

frappe.ui.form.on("Guardian Link", {
	refresh(frm) {
		// The document photo is encrypted on the server; open it through the logged viewer.
		const open = (file) => window.open("/api/method/anumati.api.v1.evidence.view?file_url=" + encodeURIComponent(file), "_blank", "noopener");
		if (frm.doc.evidence) {
			frm.add_custom_button(__("View order or document"), () => open(frm.doc.evidence));
		}
		if (frm.doc.id_document) {
			frm.add_custom_button(__("View guardian's ID"), () => open(frm.doc.id_document));
		}
	},
});
