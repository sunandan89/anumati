// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

// Colours: green granted, red withdrawal, amber waiting for confirmation, grey refused.
frappe.listview_settings["Consent Event"] = {
	add_fields: ["action", "verification_status", "short_code"],
	get_indicator(doc) {
		if (doc.action === "withdraw") return [__("Withdrawal"), "red", "action,=,withdraw"];
		if (doc.action === "refuse") return [__("Refused all"), "gray", "action,=,refuse"];
		if (doc.verification_status === "unconfirmed") return [__("Waiting"), "orange", "verification_status,=,unconfirmed"];
		return [doc.action === "renew" ? __("Renewed") : __("Granted"), "green", "action,=," + doc.action];
	},
	onload(listview) {
		// Receipt code search: type AN-XXXXXX (or just the six letters) to find a record.
		listview.page.add_field({
			fieldtype: "Data", fieldname: "receipt", label: __("Receipt code, e.g. AN-7K2Q9C"),
			change() {
				let code = (this.get_value() || "").trim().toUpperCase();
				if (code && !code.startsWith("AN-")) code = "AN-" + code;
				listview.filter_area.remove("short_code");
				if (code) listview.filter_area.add([["Consent Event", "short_code", "=", code]]);
			},
		});
	},
};
