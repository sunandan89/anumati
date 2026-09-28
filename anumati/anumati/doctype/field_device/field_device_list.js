// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

frappe.listview_settings["Field Device"] = {
	add_fields: ["status", "last_sync", "pending_events"],
	get_indicator(doc) {
		if (["lost", "wipe_queued"].includes(doc.status)) return [__("Wipe queued"), "red", "status,in,lost,wipe_queued"];
		if (doc.status === "wiped") return [__("Wiped"), "gray", "status,=,wiped"];
		if (doc.status === "logged_out") return [__("Signed out"), "gray", "status,=,logged_out"];
		const stale = !doc.last_sync || doc.last_sync < moment().subtract(2, "days").format("YYYY-MM-DD HH:mm:ss");
		if (stale) return [__("Not synced"), "orange", "status,=,active"];
		if (doc.pending_events) return [__("{0} waiting to sync", [doc.pending_events]), "orange", "status,=,active"];
		return [__("Active"), "green", "status,=,active"];
	},
};
