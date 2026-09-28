"""Voice, v1: /api/v2/method/anumati.api.v1.voice.hear

A field worker's phone sends a short clip of someone answering the notice ("haan", "nahi") and gets back
what Sarvam heard and whether it sounds like yes, no or unclear. A hint for the worker only: the clip
and transcript are not stored or logged, and the recorded consent is still the worker's decision.
Off unless the admin switches on Anumati Settings > Help recognise a spoken yes or no."""

import base64
import binascii

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint

from anumati import voice

ROLES = {"Anumati Field Worker", "Anumati Operator", "Anumati Admin", "Anumati DPO", "System Manager"}
MAX_BYTES = 2 * 1024 * 1024  # a 60-second clip from the app is about 360 KB


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=30, seconds=60)
def hear(audio, language=None, filename="clip.m4a"):
	if frappe.session.user == "Guest" or not ROLES & set(frappe.get_roles()):
		raise frappe.PermissionError
	if not cint(voice.settings().voice_listen_helper):
		return {"enabled": False}
	try:
		clip = base64.b64decode(audio or "", validate=True)
	except (binascii.Error, ValueError):
		frappe.throw(_("The clip could not be read."))
	if not clip or len(clip) > MAX_BYTES:
		frappe.throw(_("Send a clip of up to 60 seconds."))
	return {"enabled": True, **voice.hear(clip, str(filename)[:40], language)}
