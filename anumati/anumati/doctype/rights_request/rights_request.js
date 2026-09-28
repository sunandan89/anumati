// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

frappe.ui.form.on("Rights Request", {
	refresh(frm) {
		if (frm.doc.status === "Unmatched" && frm.doc.candidates) {
			frm.set_intro(__("Shared number: possible people are {0}. Call back or check the slip, then use Who is this for?", [frappe.utils.escape_html(frm.doc.candidates)]), "orange");
		} else if (frm.doc.status === "Unmatched") {
			frm.set_intro(__("Not matched yet. Find the person by their receipt code or ID, then use Who is this for?"), "orange");
		}
		if (!frm.is_new() && frm.doc.status === "Unmatched" && frm.doc.candidates && frm.perm[0] && frm.perm[0].write) {
			frm.add_custom_button(__("Who is this for?"), () => pick_person(frm)).addClass("btn-primary");
		}
		show_due(frm);
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

// Days left on the SLA, shown above the form.
function show_due(frm) {
	if (!frm.doc.sla_due || ["Closed", "Rejected"].includes(frm.doc.status)) return;
	const days = frappe.datetime.get_day_diff(frm.doc.sla_due, frappe.datetime.get_today());
	const text = days < 0 ? __("Overdue by {0} days", [-days]) : days === 0 ? __("Due today") : __("{0} days left", [days]);
	frm.dashboard.set_headline_alert(
		`<b>${text}</b> · ${__("due {0}", [frappe.datetime.str_to_user(frm.doc.sla_due)])}`,
		days < 3 ? "red" : days < 10 ? "orange" : "blue"
	);
}

// Shared number: list the people behind it (name and masked phone, each view logged) and set one.
async function pick_person(frm) {
	const refs = frm.doc.candidates.split(",").map((s) => s.trim()).filter(Boolean);
	const people = await frappe.db.get_list("Data Principal", {
		filters: { principal_ref: ["in", refs] }, fields: ["name", "principal_ref"], limit: 20,
	});
	const shown = await Promise.all(people.map((p) =>
		frappe.call({ method: "anumati.api.v1.principal.reveal", args: { principal: p.name }, type: "GET" })
			.then((r) => ({ ...p, ...(r.message || {}) }))
			.catch(() => p)
	));
	const label = (p) => [p.principal_ref, p.full_name, p.phone_masked].filter(Boolean).join(" · ");
	const d = new frappe.ui.Dialog({
		title: __("Who is this for?"),
		fields: [
			{ fieldtype: "HTML", options: `<p class="text-muted">${__("Several people share this number. Call back or check the slip, then pick the person.")}</p>` },
			{ fieldtype: "Select", fieldname: "who", label: __("Person"), reqd: 1,
			  options: shown.map((p) => ({ value: p.name, label: label(p) })) },
		],
		primary_action_label: __("Match"),
		primary_action(values) {
			d.hide();
			frm.set_value("matched_principal", values.who).then(() => frm.save());
		},
	});
	d.show();
}
