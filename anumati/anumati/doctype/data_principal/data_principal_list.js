// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

// Names and phones are encrypted, so the stock search box cannot see them. This adds a
// "Name or phone" box (whole words of a name, a full phone number, a receipt code or an ID) and
// shows each row's name and masked phone, fetched for the rows on screen only; each is logged.
frappe.listview_settings["Data Principal"] = {
	add_fields: ["is_minor", "shared_phone", "no_phone", "merged_into"],

	get_indicator(doc) {
		if (doc.merged_into) return [__("Merged"), "gray", "merged_into,is,set"];
		if (doc.is_minor) return [__("Minor"), "purple", "is_minor,=,1"];
		if (doc.shared_phone) return [__("Shared phone"), "orange", "shared_phone,=,1"];
		if (doc.no_phone) return [__("No phone"), "gray", "no_phone,=,1"];
		return [__("Adult"), "blue", "is_minor,=,0"];
	},

	onload(listview) {
		const field = listview.page.add_field({
			fieldtype: "Data",
			fieldname: "anumati_find",
			label: __("Name or phone"),
			placeholder: __("Name, phone number or receipt code"),
			change() {
				const q = (field.get_value() || "").trim();
				listview.filter_area.remove("name");
				if (!q) return listview.refresh();
				frappe.call({ method: "anumati.api.v1.principal.search", args: { q }, type: "GET" }).then((r) => {
					const found = (r.message && r.message.principals) || [];
					if (!found.length) {
						frappe.show_alert({ message: __("No one found. Names match whole words, and phone numbers must be complete."), indicator: "orange" });
					}
					listview.filter_area.add([["Data Principal", "name", "in", found.length ? found : ["-"]]]);
				});
			},
		});
		$(field.input).attr("autocomplete", "off");
	},

	refresh(listview) {
		const names = (listview.data || []).map((d) => d.name).slice(0, 100);
		if (!names.length) return;
		frappe.call({
			method: "anumati.api.v1.principal.reveal_many",
			args: { principals: names },
		}).then((r) => {
			const people = r.message || {};
			listview.$result.find(".anumati-who").remove();
			names.forEach((name) => {
				const p = people[name];
				if (!p || !(p.full_name || p.phone_masked)) return;
				const $row = listview.$result.find(`.list-row-checkbox[data-name="${CSS.escape(name)}"]`).closest(".list-row");
				const text = [p.full_name, p.phone_masked].filter(Boolean).join(" · ");
				$row.find(".list-subject").append($('<span class="anumati-who text-muted small ellipsis"></span>').text(" " + text));
			});
		});
	},
};
