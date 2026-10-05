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

// Record withdrawal: tick the optional uses to stop (all ticked to start), or leave the programme. Essential
// uses are not on the list: as in the field app, they stop only when the person leaves.
function record_withdrawal(frm) {
	frappe.call({
		method: "anumati.api.v1.rights.withdrawable",
		args: { request: frm.doc.name },
		type: "GET",
		callback: (r) => {
			const uses = r.message || [];
			if (!uses.length) {
				frappe.msgprint(__("Nothing is on for this person, so there is nothing to withdraw. Write the resolution and close the request."));
				return;
			}
			const programmes = [...new Set(uses.map((u) => u.programme))];
			const label = (p) => uses.find((u) => u.programme === p).programme_name;
			const fields = [
				{ fieldname: "programme", fieldtype: "Select", label: __("Programme"), reqd: 1,
				  options: programmes.map((p) => ({ value: p, label: label(p) })), default: programmes[0],
				  hidden: programmes.length === 1 ? 1 : 0 },
			];
			programmes.forEach((p, i) => {
				const optional = uses.filter((u) => u.programme === p && !u.essential);
				const essential = uses.filter((u) => u.programme === p && u.essential).map((u) => u.title);
				const when = `eval:doc.programme==${JSON.stringify(p)} && !doc.leave_programme`;
				if (optional.length) {
					fields.push({
						fieldname: `uses_${i}`, fieldtype: "MultiCheck", columns: 1, depends_on: when,
						label: __("Uses to stop in {0}", [label(p)]),
						options: optional.map((u) => ({ label: u.title, value: u.code, checked: 1 })),
					});
				}
				if (essential.length) {
					fields.push({
						fieldname: `essential_${i}`, fieldtype: "HTML", depends_on: when,
						options: `<p class="text-muted small">${__("Essential, stops only if they leave the programme: {0}",
							[frappe.utils.escape_html(essential.join(", "))])}</p>`,
					});
				}
			});
			fields.push(
				{ fieldname: "leave_programme", fieldtype: "Check", label: __("Leave the programme"),
				  description: __("Stops every use, essential ones too. The programme stops serving them and their retention clock starts.") },
			);
			const d = new frappe.ui.Dialog({
				title: __("Record withdrawal"),
				fields,
				primary_action_label: __("Withdraw"),
				primary_action(values) {
					const i = programmes.indexOf(values.programme);
					const picked = values[`uses_${i}`] || [];
					if (!values.leave_programme && !picked.length) {
						frappe.msgprint(__("Tick at least one optional use to stop, or Leave the programme."));
						return;
					}
					frappe.call({
						method: "anumati.api.v1.rights.fulfil_withdrawal",
						args: { request: frm.doc.name, programme: values.programme,
						        purposes: values.leave_programme ? null : picked,
						        leave_programme: values.leave_programme ? 1 : 0 },
						freeze: true,
						callback: (res) => {
							d.hide();
							frappe.show_alert({ message: __("Withdrawal recorded: {0}", [res.message.short_code]), indicator: "green" });
							frm.reload_doc();
						},
					});
				},
			});
			d.show();
		},
	});
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
