// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

frappe.listview_settings["Grievance"] = {
	add_fields: ["status", "sla_due", "dpo_since", "person_says"],
	get_indicator(doc) {
		const filter = "status,=," + doc.status;
		if (doc.status === "request_closed") return [__("request_closed"), "green", filter];
		if (doc.status === "request_answered") return [__("request_answered"), "cyan", filter];
		const dpo = doc.dpo_since ? ` · ${__("With the DPO")}` : "";
		if (doc.person_says === "not_happy") return [__("Not happy") + dpo, "red", filter];
		if (doc.sla_due && doc.sla_due < frappe.datetime.get_today()) return [__("Late") + dpo, "red", filter];
		if (doc.status === "who_is_this") return [__("who_is_this"), "red", filter];
		if (doc.status === "new_request") return [__("new_request") + dpo, doc.dpo_since ? "red" : "blue", filter];
		if (doc.status === "waiting_for_person") return [__("waiting_for_person") + dpo, "yellow", filter];
		return [__(doc.status) + dpo, doc.dpo_since ? "red" : "orange", filter];
	},
	onload(listview) {
		listview.page.add_inner_button(__("Grievance Register"), () => frappe.set_route("query-report", "Grievance Register"));
	},
};
