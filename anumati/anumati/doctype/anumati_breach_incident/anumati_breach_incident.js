// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

const BREACH = "anumati.anumati.doctype.anumati_breach_incident.breach_incident.";
const LANG_NAME = { hi: "हिन्दी", en: "English" };

frappe.ui.form.on("Anumati Breach Incident", {
	refresh(frm) {
		show_deadline(frm);
		if (!frm.is_new()) refresh_notify(frm);
	},
	notify_audience: (frm) => refresh_notify(frm),
	notify_ids: (frm) => refresh_notify(frm),
	what_happened_en: (frm) => refresh_notify(frm),
	what_happened_hi: (frm) => refresh_notify(frm),
	can_do_en: (frm) => refresh_notify(frm),
	can_do_hi: (frm) => refresh_notify(frm),
});

frappe.ui.form.on("Anumati Breach Visit", {
	told(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.told && !row.told_on) frappe.model.set_value(cdt, cdn, "told_on", frappe.datetime.get_today());
	},
});

// The Board must be told within 72 hours of discovery. Show the time left until "Board intimated" is set.
function show_deadline(frm) {
	if (!frm.doc.detected_on || frm.doc.status === "Closed") return;
	if (frm.doc.board_intimated_on) {
		frm.dashboard.set_headline_alert(
			__("Board told on {0}", [frappe.datetime.str_to_user(frm.doc.board_intimated_on)]), "green");
		return;
	}
	const deadline = moment(frm.doc.detected_on).add(72, "hours");
	const hours = Math.floor(deadline.diff(moment(), "hours", true));
	const text = hours < 0
		? __("72-hour deadline passed {0} hours ago. Tell the Data Protection Board now.", [-hours])
		: __("{0} hours left to tell the Data Protection Board (deadline {1})", [hours, frappe.datetime.str_to_user(deadline.format("YYYY-MM-DD HH:mm:ss"))]);
	frm.dashboard.set_headline_alert(`<b>${text}</b>`, hours < 24 ? "red" : "orange");
	if (frm.perm[0] && frm.perm[0].write) {
		frm.add_custom_button(__("Board told now"), () => frm.set_value("board_intimated_on", frappe.datetime.now_datetime()).then(() => frm.save()));
	}
}

// ---------------------------------------------------------------- Tell affected people

const esc = (s) => frappe.utils.escape_html(String(s == null ? "" : s));

function refresh_notify(frm) {
	clearTimeout(frm._notify_timer);
	frm._notify_timer = setTimeout(() => {
		const d = frm.doc;
		frappe.call({
			method: BREACH + "summary",
			args: {
				name: d.name,
				values: {
					notify_audience: d.notify_audience, notify_ids: d.notify_ids, field_device: d.field_device,
					programme: d.programme, what_happened_en: d.what_happened_en, what_happened_hi: d.what_happened_hi,
					can_do_en: d.can_do_en, can_do_hi: d.can_do_hi,
				},
			},
			callback: (r) => r.message && render_notify(frm, r.message),
		});
	}, 300);
}

function render_notify(frm, s) {
	frm._notify = s;
	const c = s.counts;
	const langs = Object.entries(c.languages).map(([l, n]) => `${esc(LANG_NAME[l] || l)} ${n}`).join(" · ");
	frm.get_field("notify_counts").$wrapper.html(frm.doc.notify_audience ? `
		<div style="border:1px dashed var(--border-color);border-radius:8px;padding:12px">
			<div style="display:flex;gap:28px;flex-wrap:wrap">
				<div><div style="font-size:20px;font-weight:600">${c.total}</div><div class="text-muted small">${__("people affected")}</div></div>
				<div><div style="font-size:20px;font-weight:600">${c.sms}</div><div class="text-muted small">${__("by SMS ({0} own · {1} guardian’s)", [c.own, c.guardian])}</div></div>
				<div><div style="font-size:20px;font-weight:600">${c.no_phone}</div><div class="text-muted small">${__("no phone: field visit")}</div></div>
			</div>
			<div class="text-muted small" style="margin-top:10px">${langs ? langs + ". " : ""}${__("Includes people who withdrew or left: a breach notice is a legal duty, not a use of their data. A child’s or guarded adult’s message goes to the guardian.")}</div>
		</div>` : `<div class="text-muted small">${__("Choose who to tell.")}</div>`);

	frm.get_field("notify_preview").$wrapper.html(s.previews.map((p) => `
		<div style="margin-bottom:12px">
			<div class="text-muted small">${esc(LANG_NAME[p.language] || p.language)} · ${__("{0} people", [p.people])} · ${__("{0} SMS parts", [p.parts])}${p.approved ? "" : " · " + __("template not approved yet")}</div>
			<div style="background:var(--control-bg);border-radius:12px 12px 12px 3px;padding:10px 12px;margin-top:4px;max-width:560px;line-height:1.45">${esc(p.text) || __("No breach-notice template for this language yet.")}</div>
		</div>`).join("") + `<div class="text-muted small">${__("The code at the end is each person’s own latest receipt code, so they can quote it.")}</div>`);

	frm.set_intro("");
	if (s.results) {
		const r = s.results;
		frm.set_intro(__("Breach notice sent {0} by {1}. Delivered {2} · waiting {3} · failed {4}. 72-hour steps updated.",
			[frappe.datetime.str_to_user(frm.doc.notify_sent_on), esc(frm.doc.notify_sent_by), r.delivered, r.waiting, r.failed]), "blue");
		if (frm.doc.notify_delivered !== r.delivered || frm.doc.notify_failed !== r.failed) {
			frm.doc.notify_delivered = r.delivered;
			frm.doc.notify_failed = r.failed;
			frm.refresh_fields(["notify_delivered", "notify_failed"]);
		}
	} else if (frm.doc.notify_audience && !s.ready) {
		frm.set_intro(`<b>${__("Sending SMS is off:")}</b> ${esc(s.reason)} ${__("Meanwhile, use the field visit list.")}`, "yellow");
	}
	add_notify_buttons(frm, s);
}

function add_notify_buttons(frm, s) {
	const group = __("Tell affected people");
	["Send a test to my phone", "Send to affected people…", "Retry failed", "Download field visit list", "Print notice for visits"]
		.forEach((b) => frm.remove_custom_button(__(b), group));
	const sent = !!frm.doc.notify_sent_on;
	if (s.can_send && s.ready && !sent) {
		frm.add_custom_button(__("Send a test to my phone"), () => send_test(frm), group);
		frm.add_custom_button(__("Send to affected people…"), () => confirm_send(frm), group);
	}
	if (s.can_send && sent && s.results && s.results.failed) {
		frm.add_custom_button(__("Retry failed"), () => frappe.call({
			method: BREACH + "retry", args: { name: frm.doc.name }, freeze: true,
			callback: (r) => { frappe.show_alert(__("{0} of {1} sent", [r.message.sent, r.message.retried])); frm.reload_doc(); },
		}), group);
	}
	if ((frm.doc.visit_list || []).length) {
		frm.add_custom_button(__("Download field visit list"), () => download_visits(frm), group);
	}
	if (s.previews.some((p) => p.text)) {
		frm.add_custom_button(__("Print notice for visits"), () => print_notice(frm, s), group);
	}
}

function send_test(frm) {
	const go = () => frappe.call({
		method: BREACH + "send_test", args: { name: frm.doc.name }, freeze: true,
		callback: (r) => frappe.show_alert({ message: __("Test sent to {0}", [r.message.to]), indicator: "green" }),
	});
	frm.is_dirty() ? frm.save().then(go) : go();
}

function confirm_send(frm) {
	const open = () => {
		const s = frm._notify;
		if (s.missing.length) {
			frappe.msgprint(__("Fill in: {0}", [s.missing.join(", ")]));
			return;
		}
		const c = s.counts;
		const d = new frappe.ui.Dialog({
			title: __("Send the breach notice to {0} people?", [c.sms]),
			fields: [
				{ fieldtype: "HTML", options: `<table class="table table-sm">
					<tr><td class="text-muted">${__("By SMS")}</td><td><b>${c.sms}</b> (${__("{0} own phone · {1} guardian’s", [c.own, c.guardian])})</td></tr>
					<tr><td class="text-muted">${__("Field visit list")}</td><td><b>${c.no_phone}</b> ${__("people without a phone")}</td></tr>
					<tr><td class="text-muted">${__("Cost (approx.)")}</td><td>${__("{0} SMS parts · about ₹{1}", [s.estimate.parts, s.estimate.rupees])}</td></tr>
					<tr><td class="text-muted">${__("Sent from")}</td><td>${esc(s.sender || "")} · ${__("approved breach notice")}</td></tr></table>
					<div class="alert alert-warning small">${__("This can’t be undone. Each message is logged against the person’s ID, never their number.")}</div>` },
				{ fieldname: "confirm", fieldtype: "Int", label: __("Type {0} to confirm", [c.sms]), reqd: 1 },
			],
			primary_action_label: __("Send to {0} people", [c.sms]),
			primary_action(values) {
				if (values.confirm !== c.sms) {
					frappe.msgprint(__("Type {0} to confirm.", [c.sms]));
					return;
				}
				frappe.call({
					method: BREACH + "send", args: { name: frm.doc.name, confirm: values.confirm }, freeze: true,
					callback: (r) => {
						d.hide();
						frappe.show_alert({ message: __("Sending to {0} people in the background", [r.message.queued]), indicator: "green" });
						frm.reload_doc();
					},
				});
			},
		});
		d.get_primary_btn().removeClass("btn-primary").addClass("btn-danger");
		d.show();
	};
	frm.is_dirty() ? frm.save().then(() => setTimeout(open, 400)) : open();
}

function download_visits(frm) {
	const rows = [["Beneficiary ID", "Language", "Why", "Told in person", "Told on"]].concat(
		(frm.doc.visit_list || []).map((r) => [r.principal_ref, r.language, r.reason, r.told ? "Yes" : "No", r.told_on || ""]));
	const csv = rows.map((r) => r.map((v) => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`).join(",")).join("\n");
	const a = document.createElement("a");
	a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
	a.download = `${frm.doc.name}-field-visit-list.csv`;
	a.click();
}

// A plain page with the notice in each language, for field workers to read out on visits.
function print_notice(frm, s) {
	const w = window.open("", "_blank");
	w.document.write(`<html><head><meta charset="utf-8"><title>${esc(frm.doc.name)}</title></head><body style="font-family:sans-serif;max-width:640px;margin:32px auto;line-height:1.6">
		<h2>${esc(frm.doc.name)}</h2>${s.previews.filter((p) => p.text).map((p) => `<h3>${esc(LANG_NAME[p.language] || p.language)}</h3><p style="font-size:18px">${esc(p.text)}</p>`).join("")}
		<p style="color:#666">${__("Read this to the person, tick Told in person on the field visit list, and give them their receipt code if they ask.")}</p></body></html>`);
	w.document.close();
	w.print();
}

frappe.realtime.on("anumati_breach_sent", (data) => {
	if (cur_frm && cur_frm.doctype === "Anumati Breach Incident" && cur_frm.doc.name === data.incident) cur_frm.reload_doc();
});
