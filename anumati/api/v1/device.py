"""Field devices, v1: /api/v2/method/anumati.api.v1.device.<name>

Each phone registers itself (and reports how many records it still holds) whenever it syncs. A
programme manager can mark a phone lost in Desk (Field Device > Report lost): the phone is told to wipe
itself the next time it reaches the server, and a lost-device breach incident opens with the last known
number of unsynced records (spec v0.4, breach)."""

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

WIPE_STATES = ("lost", "wipe_queued")
FREE_STATES = ("logged_out", "wiped")
FIELD_ROLE = "Anumati Field Worker"


class DeviceTakenError(frappe.PermissionError):
	pass


def _device(device_id):
	"""Only field workers check in a phone, and a phone belongs to the worker signed in on it until they
	sign out or a coordinator releases it (review C9). So nobody else can register it, or use up its wipe."""
	if frappe.session.user == "Guest" or FIELD_ROLE not in frappe.get_roles():
		raise frappe.PermissionError
	device_id = (device_id or "").strip()[:140]
	if not device_id:
		frappe.throw(_("device_id is required"))
	if not frappe.db.exists("Anumati Field Device", device_id):
		doc = frappe.new_doc("Anumati Field Device")
		doc.device_id = device_id
		return doc
	doc = frappe.get_doc("Anumati Field Device", device_id)
	if doc.user and doc.user != frappe.session.user and doc.status not in FREE_STATES:
		frappe.throw(_("This phone is signed in to another field worker. Ask your coordinator to release it "
		               "(Field Device > Status: logged_out)."), DeviceTakenError)
	return doc


@frappe.whitelist(methods=["POST"])
def register(device_id, app_version=None, model=None, pending=0):
	"""Called by the field app on sign-in and every sync. Returns {"status", "wipe"}."""
	doc = _device(device_id)
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
	# Tell the app whether to offer the spoken yes/no hint (Anumati Settings; off by default).
	helper = bool(cint(frappe.db.get_single_value("Anumati Settings", "voice_listen_helper")))
	# The worker's gender (stock User field) picks the woman's or man's recording of the notice.
	gender = (frappe.db.get_value("User", frappe.session.user, "gender") or "").lower()
	return {"status": doc.status, "wipe": wipe, "voice_helper": helper and not wipe,
	        "voice": "male" if gender == "male" else "female"}


@frappe.whitelist(methods=["POST"])
def sign_out(device_id):
	"""The field app signs out: the phone is free for the next worker to sign in on."""
	doc = _device(device_id)
	if doc.is_new() or doc.status in WIPE_STATES:
		return {"status": doc.status or "unknown"}
	doc.status = "logged_out"
	doc.flags.ignore_permissions = True
	doc.save()
	return {"status": doc.status}


@frappe.whitelist(methods=["POST"])
def report_lost(device):
	"""Desk: Field Device > Report lost. Needs write on Field Device (Programme Manager, Admin)."""
	doc = frappe.get_doc("Anumati Field Device", device)
	doc.check_permission("write")
	if doc.status in WIPE_STATES:
		return {"status": doc.status, "incident": None}
	doc.status = "wipe_queued"
	doc.reported_lost_on = now_datetime()
	doc.reported_lost_by = frappe.session.user
	doc.save()
	incident = frappe.get_doc({
		"doctype": "Anumati Breach Incident", "breach_type": "lost_device", "detected_on": now_datetime(),
		"field_device": doc.name, "principals_affected": cint(doc.pending_events),
		"description": _("Phone {0} reported lost. Unsynced records at its last sync: {1}. "
		                 "It will wipe itself if it connects again.").format(doc.name, cint(doc.pending_events)),
	})
	incident.flags.ignore_permissions = True
	incident.insert()
	return {"status": doc.status, "incident": incident.name}
