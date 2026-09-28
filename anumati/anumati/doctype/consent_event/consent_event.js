// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

// Evidence is encrypted on the server. Staff play or view it through anumati.api.v1.evidence.view,
// which decrypts in memory and logs the view. The beneficiary's name and masked phone come from
// principal.reveal (also logged); the full number never reaches the browser.
const ACTION = {
	grant: [__("Granted"), "green"], withdraw: [__("Withdrawal"), "red"],
	refuse: [__("Refused all"), "gray"], renew: [__("Renewed"), "green"],
};

frappe.ui.form.on("Consent Event", {
	refresh(frm) {
		anumati_show_principal(frm, frm.doc.principal);
		anumati_summary(frm);
		if (!frm.is_new() && frm.doc.hash) {
			frm.add_custom_button(__("Check signature"), () =>
				frappe.call({ method: "anumati.api.v1.consent.verify", args: { hash: frm.doc.hash } }).then((r) => {
					const v = r.message || {};
					const ok = v.in_chain && v.signature_valid;
					frappe.msgprint({
						title: ok ? __("Signature is valid") : __("Signature check failed"),
						indicator: ok ? "green" : "red",
						message: ok
							? __("This record is number {0} on the signed chain (key {1}). It has not been changed since it was recorded.", [v.chain_seq, frappe.utils.escape_html(v.key_id || "")])
							: __("This record's signature does not verify. Tell the DPO."),
					});
				})
			);
		}
		const field = frm.fields_dict.evidence;
		if (!field) return;
		field.$wrapper.find(".anumati-evidence").remove();
		let items = [];
		try {
			items = typeof frm.doc.evidence === "string" ? JSON.parse(frm.doc.evidence || "[]") : frm.doc.evidence || [];
		} catch (e) {
			items = [];
		}
		if (!items.length) return;
		const $box = $('<div class="anumati-evidence" style="margin-top:8px;display:flex;flex-direction:column;gap:12px"></div>');
		items.forEach((e) => {
			if (!e || !e.file) return;
			const url = "/api/method/anumati.api.v1.evidence.view?file_url=" + encodeURIComponent(e.file);
			const kind = (e.kind || "").toLowerCase();
			const label = frappe.utils.escape_html(kind || __("Evidence"));
			const $item = $('<div style="border:1px solid var(--border-color);border-radius:8px;padding:8px"></div>');
			$item.append(`<div class="text-muted small" style="margin-bottom:6px">${label}</div>`);
			if (kind === "audio" || /\.(m4a|aac|mp3|wav|ogg)$/i.test(e.file)) {
				$item.append($("<audio controls preload='none' style='width:100%'></audio>").attr("src", url));
			} else {
				$item.append(
					$("<a target='_blank' rel='noopener'></a>").attr("href", url).append(
						$("<img style='max-width:100%;max-height:320px;border-radius:6px' loading='lazy'>").attr("src", url).attr("alt", label)
					)
				);
			}
			$box.append($item);
		});
		field.$wrapper.append($box);
	},
});

function anumati_show_principal(frm, principal) {
	if (!principal) return;
	frappe.call({ method: "anumati.api.v1.principal.reveal", args: { principal }, type: "GET" }).then((r) => {
		const p = r.message || {};
		const parts = [p.full_name, p.phone_masked, p.principal_ref].filter(Boolean).map(frappe.utils.escape_html);
		if (parts.length) frm.set_intro(__("Beneficiary: {0}", [parts.join(" · ")]), "blue");
	});
}

// Summary tab: what happened, in plain words. Purpose codes only; no personal data beyond the header.
function anumati_summary(frm) {
	const field = frm.fields_dict.summary_html;
	if (!field || frm.is_new()) return;
	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));
	const list = (v) => {
		try {
			const a = typeof v === "string" ? JSON.parse(v || "[]") : v || [];
			return Array.isArray(a) ? a : [];
		} catch (e) {
			return [];
		}
	};
	const d = frm.doc;
	const [label, color] = ACTION[d.action] || [d.action, "gray"];
	const chips = (items, tone) =>
		items.map((p) => `<span class="indicator-pill ${tone}" style="margin:0 6px 6px 0">${esc(p)}</span>`).join("") ||
		`<span class="text-muted">${__("None")}</span>`;
	const row = (k, v) => (v ? `<div style="display:flex;gap:12px;padding:6px 0;border-bottom:1px solid var(--border-color)"><span class="text-muted" style="width:170px;flex-shrink:0">${k}</span><span>${v}</span></div>` : "");
	const when = d.device_time ? frappe.datetime.str_to_user(d.device_time) : "";
	field.$wrapper.html(`
		<div style="border:1px solid var(--border-color);border-radius:12px;padding:16px 18px;margin-bottom:12px">
			<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px">
				<span class="indicator-pill ${color}">${esc(label)}</span>
				${d.short_code ? `<span style="font-family:var(--font-mono, monospace);font-size:var(--text-lg)">${esc(d.short_code)}</span>` : ""}
				<span class="text-muted">${esc(when)}</span>
			</div>
			<div style="margin-bottom:4px"><b>${__("Agreed to")}</b></div><div>${chips(list(d.purposes_granted), "green")}</div>
			<div style="margin:6px 0 4px"><b>${__("Said no to")}</b></div><div>${chips(list(d.purposes_denied), "gray")}</div>
			<div style="margin-top:10px">
				${row(__("How"), esc(frappe.utils.to_title_case((d.capture_mode || "").replace(/_/g, " "))))}
				${row(__("Verified by"), esc((d.verification_method || "").replace(/_/g, " ")) + (d.verification_status ? ` <span class="text-muted">(${esc(d.verification_status)})</span>` : ""))}
				${row(__("Notice"), esc([d.notice_version && "v" + d.notice_version, d.language, (d.notice_delivery || "").replace(/_/g, " ")].filter(Boolean).join(" · ")) + (d.notice_completed ? ` <span class="text-muted">· ${__("heard in full")}</span>` : ""))}
				${row(__("Recorded by"), esc(d.captured_by))}
				${row(__("Guardian"), d.guardian_link ? esc(d.guardian_link) : "")}
			</div>
			<div class="text-muted small" style="margin-top:10px">${__("Evidence is in the Evidence tab. Hash, signature and chain position are in the Proof tab. This record can never be edited; a change of mind is a new record.")}</div>
		</div>`);
}
