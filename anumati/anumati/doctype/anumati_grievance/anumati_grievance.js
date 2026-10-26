// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

// Grievances (anumati/grievance.py). Statuses are the plain words of rights requests; the final answer
// carries an outcome the person reads in one line above it.
const G_DONE = ["request_answered", "request_closed"];
const OUTCOMES = ["put_right", "partly_put_right", "no_problem_found"];

frappe.ui.form.on("Anumati Grievance", {
	refresh(frm) {
		const d = frm.doc;
		if (d.category === "staff_behaviour") frm.set_intro(__("Staff behaviour: only the DPO can see this grievance."), "blue");
		if (d.person_says === "not_happy" && !G_DONE.includes(d.status)) {
			frm.set_intro(__("The person said this did not solve it. Passed to the DPO."), "red");
		}
		if (d.status === "who_is_this") {
			frm.set_intro(d.candidates
				? __("Shared number: possible people are {0}. Call back or check the slip, then use Who is this for?", [frappe.utils.escape_html(d.candidates)])
				: __("Not matched yet. Find the person by their receipt code or ID, then use Who is this for?"), "orange");
			if (d.candidates && frm.perm[0] && frm.perm[0].write) {
				frm.add_custom_button(__("Who is this for?"), () => g_pick_person(frm)).addClass("btn-primary");
			}
		}
		g_show_due(frm);
		if (frm.is_new()) return;
		const canWrite = frm.perm[0] && frm.perm[0].write;
		if (d.matched_principal && d.status !== "request_closed" && canWrite) {
			const group = __("Reply to the person");
			frm.add_custom_button(__("Send update"), () => g_reply(frm, "update"), group);
			frm.add_custom_button(__("Ask a question"), () => g_reply(frm, "question"), group);
			frm.add_custom_button(__("Send final answer"), () => g_reply(frm, "answer"), group);
		}
		if (d.about_request) frm.add_custom_button(__("Open {0}", [d.about_request]), () => frappe.set_route("Form", "Anumati Rights Request", d.about_request));
		if (d.evidence) {
			frm.add_custom_button(__("View photo or document"), () =>
				window.open(`/api/method/anumati.api.v1.evidence.view?file_url=${encodeURIComponent(d.evidence)}`, "_blank"));
		}
		if (d.status !== "request_closed" && canWrite) {
			frm.add_custom_button(__("Move to rights requests"), () => g_move(frm), __("Actions"));
		}
		g_consents(frm);
	},
});

// Reply to the person: update (stays Working on it), question (Waiting for the person) or the final answer
// with its outcome (Answered). The person reads it on the self-service page and can write back.
function g_reply(frm, kind) {
	const titles = { update: __("Send update"), question: __("Ask a question"), answer: __("Send final answer") };
	const hints = {
		update: __("For example: We are checking with the field team. The status stays Working on it."),
		question: __("Ask what you need to know. The status becomes Waiting for the person until they reply."),
		answer: __("Your answer to the request. The status becomes Answered."),
	};
	const fields = [{ fieldtype: "HTML", options: `<p class="text-muted small">${hints[kind]} ${__("Plain words, no names of other people.")}</p>` }];
	if (kind === "answer") {
		fields.push({ fieldname: "outcome", fieldtype: "Select", label: __("Outcome"), reqd: 1,
		              options: OUTCOMES.map((o) => ({ value: o, label: __(o) })) });
	}
	fields.push({ fieldname: "message", fieldtype: "Small Text", label: __("Message"), reqd: 1 });
	const d = new frappe.ui.Dialog({
		title: titles[kind], fields, primary_action_label: __("Send"),
		primary_action(values) {
			frappe.call({
				method: "anumati.api.v1.grievance.reply",
				args: { grievance: frm.doc.name, message: values.message, kind, outcome: values.outcome || null },
				freeze: true,
				callback: () => { d.hide(); frappe.show_alert({ message: __("Sent"), indicator: "green" }); frm.reload_doc(); },
			});
		},
	});
	d.show();
}

function g_move(frm) {
	const types = ["withdrawal", "access", "correction", "erasure", "nomination"];
	frappe.prompt({ fieldname: "request_type", fieldtype: "Select", label: __("What did they ask for?"), reqd: 1,
	                options: types.map((t) => ({ value: t, label: __(t) })) },
		(v) => frappe.call({
			method: "anumati.api.v1.grievance.move_to_request", args: { grievance_name: frm.doc.name, request_type: v.request_type },
			freeze: true, callback: (r) => frappe.set_route("Form", "Anumati Rights Request", r.message.request),
		}), __("Move to rights requests"));
}

function g_show_due(frm) {
	const d = frm.doc;
	if (!d.sla_due || G_DONE.includes(d.status)) return;
	const days = frappe.datetime.get_day_diff(d.sla_due, frappe.datetime.get_today());
	const text = days < 0 ? __("Late by {0} days", [-days]) : days === 0 ? __("Reply due today") : __("{0} days left to reply", [days]);
	const dpo = d.dpo_since ? ` · ${__("With the DPO")}` : "";
	frm.dashboard.set_headline_alert(`<b>${text}</b>${dpo} · ${__("reply by {0}", [frappe.datetime.str_to_user(d.sla_due)])}`,
		days < 3 || d.dpo_since ? "red" : days < 10 ? "orange" : "blue");
}

// The person's consents, for context: each use, on or off, with the latest receipt. No names or numbers.
async function g_consents(frm) {
	const wrapper = frm.get_field("consents_html").$wrapper;
	if (!frm.doc.matched_principal) return wrapper.html("");
	const states = await frappe.db.get_list("Anumati Consent State", {
		filters: { principal: frm.doc.matched_principal }, fields: ["programme", "purpose", "status", "last_event", "updated"], limit: 100,
	}).catch(() => []);
	if (!states.length) return wrapper.html(`<p class="text-muted">${__("Nothing recorded yet.")}</p>`);
	const titles = Object.fromEntries((await frappe.db.get_list("Anumati Purpose", {
		filters: { name: ["in", states.map((s) => s.purpose)] }, fields: ["name", "purpose_title"], limit: 100,
	}).catch(() => [])).map((p) => [p.name, p.purpose_title]));
	const esc = frappe.utils.escape_html;
	wrapper.html(`<table class="table table-sm"><tbody>${states.map((s) => `<tr>
		<td>${esc(s.programme)}</td><td>${esc(titles[s.purpose] || s.purpose)}</td><td>${esc(__(s.status))}</td>
		<td class="text-muted">${esc(frappe.datetime.str_to_user(s.updated || ""))}</td>
		<td>${s.last_event ? `<a href="/app/anumati-consent-event/${encodeURIComponent(s.last_event)}">${__("Open")}</a>` : ""}</td></tr>`).join("")}</tbody></table>`);
}

// Shared number: list the people behind it (name and masked phone, each view logged) and set one.
async function g_pick_person(frm) {
	const refs = frm.doc.candidates.split(",").map((s) => s.trim()).filter(Boolean);
	const people = await frappe.db.get_list("Anumati Data Principal", { filters: { principal_ref: ["in", refs] }, fields: ["name", "principal_ref"], limit: 20 });
	const shown = await Promise.all(people.map((p) =>
		frappe.call({ method: "anumati.api.v1.principal.reveal", args: { principal: p.name }, type: "GET" })
			.then((r) => ({ ...p, ...(r.message || {}) })).catch(() => p)));
	const label = (p) => [p.principal_ref, p.full_name, p.phone_masked].filter(Boolean).join(" · ");
	frappe.prompt({ fieldtype: "Select", fieldname: "who", label: __("Person"), reqd: 1, options: shown.map((p) => ({ value: p.name, label: label(p) })) },
		(v) => frm.set_value("matched_principal", v.who).then(() => frm.save()), __("Who is this for?"), __("Match"));
}
