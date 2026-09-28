// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

frappe.listview_settings["Rights Request"] = {
	add_fields: ["status", "sla_due"],
	get_indicator(doc) {
		if (["Closed", "Rejected"].includes(doc.status)) return [__(doc.status), doc.status === "Closed" ? "green" : "gray", "status,=," + doc.status];
		if (doc.sla_due && doc.sla_due < frappe.datetime.get_today()) return [__("Overdue"), "red", "status,=," + doc.status];
		if (doc.status === "Unmatched") return [__("Unmatched"), "red", "status,=,Unmatched"];
		return [__(doc.status), doc.status === "Open" ? "blue" : "orange", "status,=," + doc.status];
	},
	onload(listview) {
		listview.page.add_inner_button(__("Requests board"), () => frappe.set_route("List", "Rights Request", "Kanban", "Requests"));
		listview.page.add_inner_button(__("Assigned to me"), () => {
			listview.filter_area.clear(false).then(() => listview.filter_area.add([["Rights Request", "assigned_to", "=", frappe.session.user]]));
		});
	},
};
