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
		if (frm.is_new() || !open || !frm.doc.matched_principal) return;
		const type = frm.doc.request_type;
		if (type === "access") {
			frm.add_custom_button(__("Send data summary"), () => act(frm, "send_summary", {}, __("Summary prepared"))).addClass("btn-primary");
		} else if (type === "correction") {
			frm.set_intro(__("Edit the principal's record first, then press Mark corrected. Only the changed field names are recorded."), "blue");
			frm.add_custom_button(__("Mark corrected"), () => act(frm, "mark_corrected", {}, __("Closed"))).addClass("btn-primary");
		} else if (type === "nomination") {
			frm.add_custom_button(__("Add nominee"), () => add_nominee(frm)).addClass("btn-primary");
		} else if (type === "erasure" && frm.doc.status !== "Awaiting Acknowledgement") {
			frm.add_custom_button(__("Start erasure"), () => start_erasure(frm)).addClass("btn-primary");
		}
		if (type !== "withdrawal" && type !== "correction" && type !== "access" && type !== "nomination") {
			frm.add_custom_button(__("Close and notify"), () => close_request(frm, "Closed"), __("Finish"));
		}
		frm.add_custom_button(__("Reject"), () => close_request(frm, "Rejected"), __("Finish"));
		frm.add_custom_button(__("Reply with a template"), () => reply(frm), __("Finish"));
	},
});

function act(frm, method, args, message) {
	frappe.call({
		method: `anumati.api.v1.rights.${method}`,
		args: { request: frm.doc.name, ...args },
		freeze: true,
		callback: () => {
			frappe.show_alert({ message, indicator: "green" });
			frm.reload_doc();
		},
	});
}

function start_erasure(frm) {
	frappe.prompt(
		[
			{ fieldname: "programme", fieldtype: "Link", options: "Programme", label: __("Programme (optional)"), default: frm.doc.programme },
			{ fieldname: "note", fieldtype: "HTML",
			  options: `<p class="text-muted small">${__("Withdraws every optional purpose, then asks each system to erase. Purposes kept under a legal obligation go on legal hold for the DPO to review.")}</p>` },
		],
		(values) => act(frm, "start_erasure", { programme: values.programme || null }, __("Erasure started")),
		__("Start erasure"),
		__("Start")
	);
}

function add_nominee(frm) {
	frappe.prompt(
		[
			{ fieldname: "nominee_name", fieldtype: "Data", label: __("Nominee name"), reqd: 1 },
			{ fieldname: "relation", fieldtype: "Data", label: __("Relation"), reqd: 1 },
			{ fieldname: "contact", fieldtype: "Data", label: __("Contact (optional)") },
		],
		(values) => act(frm, "add_nominee", values, __("Nominee recorded")),
		__("Add nominee"),
		__("Save")
	);
}

function close_request(frm, status) {
	frappe.prompt(
		[{ fieldname: "resolution", fieldtype: "Small Text", label: __("What was done"), reqd: status === "Rejected" }],
		(values) => act(frm, "close", { status, resolution: values.resolution || null }, __("Done; the person is told in their language")),
		status === "Rejected" ? __("Reject request") : __("Close and notify"),
		status === "Rejected" ? __("Reject") : __("Close")
	);
}

function reply(frm) {
	frappe.prompt(
		[{ fieldname: "template_event", fieldtype: "Select", label: __("Template"), default: "rights_update", reqd: 1,
		   options: ["rights_update", "access_summary", "reminder"] }],
		(values) => act(frm, "reply", values, __("Reply sent")),
		__("Reply with an approved template"),
		__("Send")
	);
}

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
