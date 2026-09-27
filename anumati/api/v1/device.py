"""Field devices, v1: /api/v2/method/anumati.api.v1.device.<name>

Each phone registers itself (and reports how many records it still holds) whenever it syncs. A
programme manager can mark a phone lost in Desk (Field Device > Report lost): the phone is told to wipe
itself the next time it reaches the server, and a lost-device breach incident opens with the last known
number of unsynced records (spec v0.4, breach)."""

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

WIPE_STATES = ("lost", "wipe_queued")


@frappe.whitelist(methods=["POST"])
def register(device_id, app_version=None, model=None, pending=0):
	"""Called by the field app on sign-in and every sync. Returns {"status", "wipe"}."""
	if frappe.session.user == "Guest":
		raise frappe.PermissionError
	device_id = (device_id or "").strip()[:140]
	if not device_id:
		frappe.throw(_("device_id is required"))
	if frappe.db.exists("Field Device", device_id):
		doc = frappe.get_doc("Field Device", device_id)
	else:
		doc = frappe.new_doc("Field Device")
		doc.device_id = device_id
	wipe = doc.status in WIPE_STATES
	if wipe:
		doc.status = "wiped"
		doc.wiped_on = now_datetime()
	else:
		doc.status = "active"
		doc.user = frappe.session.user
	doc.app_version = (app_version or "")[:140] or doc.app_version
	doc.model = (model or "")[:140] or doc.model
	doc.pending_events = cint(pending)
	doc.last_sync = now_datetime()
	doc.flags.ignore_permissions = True
	doc.save()
	return {"status": doc.status, "wipe": wipe}


@frappe.whitelist(methods=["POST"])
def report_lost(device):
	"""Desk: Field Device > Report lost. Needs write on Field Device (Programme Manager, Admin)."""
	doc = frappe.get_doc("Field Device", device)
	doc.check_permission("write")
	if doc.status in WIPE_STATES:
		return {"status": doc.status, "incident": None}
	doc.status = "wipe_queued"
	doc.reported_lost_on = now_datetime()
	doc.reported_lost_by = frappe.session.user
	doc.save()
	incident = frappe.get_doc({
		"doctype": "Breach Incident", "breach_type": "lost_device", "detected_on": now_datetime(),
		"field_device": doc.name, "principals_affected": cint(doc.pending_events),
		"description": _("Phone {0} reported lost. Unsynced records at its last sync: {1}. "
		                 "It will wipe itself if it connects again.").format(doc.name, cint(doc.pending_events)),
	})
	incident.flags.ignore_permissions = True
	incident.insert()
	return {"status": doc.status, "incident": incident.name}
