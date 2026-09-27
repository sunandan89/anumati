// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

frappe.ui.form.on("Anumati Settings", {
	refresh(frm) {
		if (!frappe.user.has_role("System Manager")) return;
		frm.add_custom_button(__("Set up field app"), () => {
			frappe.confirm(
				__("Switch on the Anumati Collect app, create the fictional DEMO programme with a published notice (English and Hindi), and create or reset the test field worker {0}?", ["fieldworker.demo@example.com"]),
				() => {
					frappe.call({
						method: "anumati.demo.setup_field_app",
						freeze: true,
						freeze_message: __("Setting up…"),
					}).then((r) => {
						const out = r.message || {};
						const rows = [
							[__("Organisation address"), frappe.utils.escape_html(out.site || "")],
							[__("User ID"), frappe.utils.escape_html(out.user || "")],
							[__("Password"), `<code>${frappe.utils.escape_html(out.password || "")}</code>`],
							[__("Programme"), frappe.utils.escape_html(out.programme || "")],
						];
						const table = rows.map(([k, v]) => `<tr><td style="padding:4px 12px 4px 0">${k}</td><td>${v}</td></tr>`).join("");
						const warn = out.message ? `<p class="text-warning">${frappe.utils.escape_html(out.message)}</p>` : "";
						frappe.msgprint({
							title: __("Field app ready"),
							indicator: "green",
							message: `${warn}<p>${__("Sign in on the phone with these. The password is shown only now; run this again to make a new one.")}</p><table>${table}</table>`,
						});
					});
				}
			);
		}, __("Actions"));
	},
});
