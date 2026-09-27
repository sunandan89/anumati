// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

frappe.ui.form.on("Rights Request", {
	refresh(frm) {
		if (frm.doc.status === "Unmatched" && frm.doc.candidates) {
			frm.set_intro(__("Shared number: possible people are {0}. Call back or check the slip, then set Matched principal.", [frappe.utils.escape_html(frm.doc.candidates)]), "orange");
		} else if (frm.doc.status === "Unmatched") {
			frm.set_intro(__("Not matched yet. Find the person by their receipt code or ID, then set Matched principal."), "orange");
		}
		const open = !["Closed", "Rejected"].includes(frm.doc.status);
		if (!frm.is_new() && open && frm.doc.request_type === "withdrawal" && frm.doc.matched_principal) {
			frm.add_custom_button(__("Record withdrawal"), () => record_withdrawal(frm)).addClass("btn-primary");
		}
	},
});

function record_withdrawal(frm) {
	frappe.prompt(
		[
			{ fieldname: "programme", fieldtype: "Link", options: "Programme", label: __("Programme"), reqd: 1 },
			{ fieldname: "note", fieldtype: "HTML",
			  options: `<p class="text-muted small">${__("Leave purposes empty to withdraw every optional purpose (the default in the spec).")}</p>` },
			{ fieldname: "purposes", fieldtype: "Small Text", label: __("Purpose codes (optional, comma-separated)") },
		],
		(values) => {
			const purposes = (values.purposes || "").split(",").map((s) => s.trim()).filter(Boolean);
			frappe.call({
				method: "anumati.api.v1.rights.fulfil_withdrawal",
				args: { request: frm.doc.name, programme: values.programme, purposes: purposes.length ? purposes : null },
				freeze: true,
				callback: (r) => {
					frappe.show_alert({ message: __("Withdrawal recorded: {0}", [r.message.short_code]), indicator: "green" });
					frm.reload_doc();
				},
			});
		},
		__("Record withdrawal"),
		__("Withdraw")
	);
}
