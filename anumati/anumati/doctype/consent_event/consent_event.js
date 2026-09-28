// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

// Evidence is encrypted on the server. Staff play or view it through anumati.api.v1.evidence.view,
// which decrypts in memory and logs the view. The beneficiary's name and masked phone come from
// principal.reveal (also logged); the full number never reaches the browser.
frappe.ui.form.on("Consent Event", {
	refresh(frm) {
		anumati_show_principal(frm, frm.doc.principal);
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
