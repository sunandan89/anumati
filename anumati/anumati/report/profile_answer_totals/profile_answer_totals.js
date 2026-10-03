// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

frappe.query_reports["Profile Answer Totals"] = {
	filters: [
		{ fieldname: "programme", label: __("Programme"), fieldtype: "Link", options: "Programme" },
		{ fieldname: "question", label: __("Question"), fieldtype: "Link", options: "Profile Question" },
	],
};
