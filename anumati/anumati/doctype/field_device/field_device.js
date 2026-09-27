// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

frappe.ui.form.on("Field Device", {
	refresh(frm) {
		if (frm.is_new() || !frm.perm[0]?.write) return;
		if (["lost", "wipe_queued", "wiped"].includes(frm.doc.status)) return;
		frm.add_custom_button(__("Report lost"), () => {
			frappe.confirm(
				__("Mark this phone lost? It will sign out and delete its data the next time it connects, and a lost-device breach incident will open. Records it has not synced ({0}) cannot be recovered.", [frm.doc.pending_events || 0]),
				() => frappe.call({ method: "anumati.api.v1.device.report_lost", args: { device: frm.doc.name }, freeze: true })
					.then((r) => {
						frm.reload_doc();
						if (r.message && r.message.incident) {
							frappe.show_alert({ message: __("Breach incident {0} opened", [r.message.incident]), indicator: "orange" });
						}
					})
			);
		}).addClass("btn-danger");
	},
});
