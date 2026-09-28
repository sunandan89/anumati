// Copyright (c) 2026, Dhwani RIS and contributors
// License: AGPL-3.0. See LICENSE

// The Board must be told within 72 hours of discovery. Show the time left until "Board intimated" is set.
frappe.ui.form.on("Breach Incident", {
	refresh(frm) {
		if (!frm.doc.detected_on || frm.doc.status === "Closed") return;
		if (frm.doc.board_intimated_on) {
			frm.dashboard.set_headline_alert(
				__("Board told on {0}", [frappe.datetime.str_to_user(frm.doc.board_intimated_on)]), "green");
			return;
		}
		const deadline = moment(frm.doc.detected_on).add(72, "hours");
		const hours = Math.floor(deadline.diff(moment(), "hours", true));
		const text = hours < 0
			? __("72-hour deadline passed {0} hours ago. Tell the Data Protection Board now.", [-hours])
			: __("{0} hours left to tell the Data Protection Board (deadline {1})", [hours, frappe.datetime.str_to_user(deadline.format("YYYY-MM-DD HH:mm:ss"))]);
		frm.dashboard.set_headline_alert(`<b>${text}</b>`, hours < 24 ? "red" : "orange");
		if (frm.perm[0] && frm.perm[0].write) {
			frm.add_custom_button(__("Board told now"), () => frm.set_value("board_intimated_on", frappe.datetime.now_datetime()).then(() => frm.save()));
		}
	},
});
