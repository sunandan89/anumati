// Stock custom chart source: counts by one field, with readable labels (anumati/charts.py).
frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Anumati Breakdown"] = {
	method: "anumati.charts.breakdown",
	filters: [],
};
