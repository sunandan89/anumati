// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

frappe.listview_settings["Rights Request"] = {
	add_fields: ["status", "sla_due"],
	get_indicator(doc) {
		const filter = "status,=," + doc.status;
		if (doc.status === "request_closed") return [__("request_closed"), "green", filter];
		if (doc.status === "cannot_do") return [__("cannot_do"), "gray", filter];
		if (doc.status === "request_answered") return [__("request_answered"), "cyan", filter];
		if (doc.sla_due && doc.sla_due < frappe.datetime.get_today()) return [__("Late"), "red", filter];
		if (doc.status === "who_is_this") return [__("who_is_this"), "red", filter];
		if (doc.status === "new_request") return [__("new_request"), "blue", filter];
		if (doc.status === "waiting_for_person") return [__("waiting_for_person"), "yellow", filter];
		return [__(doc.status), "orange", filter];
	},
	onload(listview) {
		listview.page.add_inner_button(__("Requests board"), () => frappe.set_route("List", "Rights Request", "Kanban", "Requests"));
		listview.page.add_inner_button(__("Assigned to me"), () => {
			listview.filter_area.clear(false).then(() => listview.filter_area.add([["Rights Request", "assigned_to", "=", frappe.session.user]]));
		});
	},
};
