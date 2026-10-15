// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

frappe.query_reports["Grievance Register"] = {
	filters: [
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date", default: frappe.datetime.add_months(frappe.datetime.get_today(), -12) },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date", default: frappe.datetime.get_today() },
	],
};
