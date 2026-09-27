// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE
//
// Notice builder (UI only). Publishing is enforced server-side by the "Notice Publishing" Workflow;
// this script only explains what is still missing and previews the notice as a phone would show it.

const RULE3 = {
	withdrawal_methods: __("How to withdraw consent"),
	rights_text: __("How to exercise rights"),
	board_complaint_route: __("How to complain to the Data Protection Board"),
	dpo_contact: __("DPO or grievance contact"),
	security_summary: __("Summary of security safeguards"),
};
const esc = (s) => frappe.utils.escape_html(s == null ? "" : String(s));

frappe.ui.form.on("Notice Template", {
	setup(frm) {
		// Only offer purposes and processors that belong to this notice's programme.
		frm.set_query("purpose", "purposes", () => ({ filters: { programme: frm.doc.programme } }));
		frm.set_query("purpose", "processors", () => ({ filters: { programme: frm.doc.programme } }));
	},

	onload(frm) {
		// An amended notice is a new version: make the author choose its number.
		if (frm.is_new() && frm.doc.amended_from) frm.set_value("version", "");
	},

	refresh(frm) {
		show_readiness(frm);
		if (frm.is_new()) return;
		frm.add_custom_button(__("Preview"), () => preview(frm));
		frm.add_custom_button(
			__("Translation"),
			() => frappe.new_doc("Notice Translation", { notice: frm.doc.name }),
			__("Add")
		);
	},
});

async function show_readiness(frm) {
	if (frm.is_new() || frm.doc.docstatus !== 0) return;
	const problems = Object.entries(RULE3)
		.filter(([field]) => !frm.doc[field])
		.map(([, label]) => __("Rule 3: {0} is missing", [label]));
	const purposes = (frm.doc.purposes || []).map((row) => row.purpose).filter(Boolean);
	if (!purposes.length) problems.push(__("Add at least one purpose"));
	if (purposes.length) {
		const rows = await frappe.db.get_list("ROPA Entry", {
			filters: { purpose: ["in", purposes], status: "Approved" },
			fields: ["purpose"],
			limit: 500,
		});
		const approved = new Set(rows.map((r) => r.purpose));
		purposes
			.filter((p) => !approved.has(p))
			.forEach((p) =>
				problems.push(__("{0}: record of processing (with DPIA if required) is not approved", [p]))
			);
	}
	if (problems.length) {
		frm.set_intro(
			`<b>${__("Can't publish yet")}</b><br>${problems.map(esc).join("<br>")}`,
			"orange"
		);
	} else {
		frm.set_intro(__("Ready to publish: Rule 3 contents present and every purpose's record of processing is approved."), "green");
	}
}

async function preview(frm) {
	const names = (frm.doc.purposes || []).map((row) => row.purpose).filter(Boolean);
	const [purposes, translations] = await Promise.all([
		frappe.db.get_list("Purpose", {
			filters: { name: ["in", names.length ? names : ["-"]] },
			fields: ["name", "purpose_title", "description", "essential"],
			limit: 100,
		}),
		frappe.db.get_list("Notice Translation", {
			filters: { notice: frm.doc.name },
			fields: ["language", "summary", "reviewer", "machine_translated",
				"label_yes_all", "label_no_all", "label_save"],
			limit: 50,
		}),
	]);
	const versions = [{ language: __("Base text"), summary: frm.doc.summary, reviewer: "base" }].concat(translations);
	const dialog = new frappe.ui.Dialog({
		title: __("Preview: {0}", [frm.doc.name]),
		fields: [
			{ fieldtype: "Select", fieldname: "language", label: __("Language"),
			  options: versions.map((v) => v.language), default: versions[0].language,
			  onchange: () => render() },
			{ fieldtype: "HTML", fieldname: "phone" },
		],
	});
	const render = () => {
		const v = versions.find((x) => x.language === dialog.get_value("language")) || versions[0];
		const warn = v.reviewer ? "" :
			`<div class="text-warning small">${__("Machine-made or not reviewed: the field app will not show this language yet.")}</div>`;
		const items = purposes.map((p) =>
			`<div style="border:1px solid var(--border-color);border-radius:10px;padding:8px 10px;margin:6px 0">
				<b>${esc(p.purpose_title)}</b>${p.essential ? ` <span class="text-muted small">(${__("always on")})</span>` : ""}
				<div class="small text-muted">${esc(p.description)}</div></div>`).join("");
		const yes = esc(v.label_yes_all || __("Yes to all")), no = esc(v.label_no_all || __("No to all"));
		dialog.fields_dict.phone.$wrapper.html(
			`<div style="max-width:340px;margin:auto;border:8px solid #2A2118;border-radius:28px;padding:14px">
				${warn}<p>${esc(v.summary)}</p>${items}
				<div style="display:flex;gap:8px;margin-top:10px">
					<button class="btn btn-default btn-sm" style="flex:1">${no}</button>
					<button class="btn btn-default btn-sm" style="flex:1">${yes}</button>
				</div>
				<div class="small text-muted" style="margin-top:8px">${esc(frm.doc.withdrawal_methods)}</div>
			</div>`
		);
	};
	dialog.show();
	render();
}
