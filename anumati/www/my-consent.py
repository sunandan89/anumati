# Copyright (c) 2026, Dhwani RIS and contributors
# License: AGPL-3.0. See LICENSE
"""/my-consent: the self-service page (a stock Frappe portal page; the data comes from anumati.selfservice).

Every word on the page is translated here, on the server, so the language picker in the site header (or
the browser's language) decides it. Only fixed strings go into the page: no personal data."""

import frappe
from frappe import _

no_cache = 1


def get_context(context):
	settings = frappe.get_cached_doc("Anumati Settings")
	context.no_cache = 1
	context.show_sidebar = False
	context.title = _("Your consent choices")
	context.org = settings.org_legal_name or ""
	config = {
		"org": settings.org_legal_name or "",
		"dpo_email": settings.dpo_email or "",
		"helpline": settings.get("helpline") or "",
		"reply_days": settings.get("rights_sla_days") or 30,
		"t": {k: _(v) for k, v in STRINGS.items()},
	}
	# Safe inside <script>: no "</" can close the tag.
	context.ss_config = frappe.as_json(config, indent=None).replace("</", "<\\/")
	return context


STRINGS = {
	# sign in
	"see_or_change": "See or change your consent",
	"intro": "Turn uses of your data on or off, see what you agreed to, or ask us something.",
	"mobile": "Your mobile number",
	"mobile_ph": "10-digit number",
	"mobile_help": "Yours, or your guardian's if they gave consent for you.",
	"send_code": "Send me a code",
	"no_phone": "No phone? Use your receipt code",
	"privacy": "We never show your details until you prove it's you.",
	"enter_code": "Enter the code",
	"code_sent": "If this number is with us, a code is on its way by SMS to {0}.",
	"continue": "Continue",
	"change_number": "Change number",
	"tries_left": "That code is not right. {0} tries left.",
	"not_set_up": "Sign-in by SMS is not ready yet. Use your receipt code, or ask a field worker.",
	"use_receipt": "Use your receipt code",
	"receipt_help": "It's on the paper slip you were given, like AN-7K2Q9C.",
	"receipt_code": "Receipt code",
	"birth_year": "Year of birth",
	"code_mode_note": "Signed in with a receipt code: you can turn uses off and ask us things. To turn a use on, sign in with your phone or ask a field worker.",
	"back": "Back",
	# who
	"who_are_you": "Who are you?",
	"who_are_you_help": "This number is linked to more than one person. Choose your name and confirm your year of birth.",
	"who_for": "Who are you here for?",
	"rel_self": "You",
	"rel_child": "Your child · you are the guardian",
	"rel_guarded": "You are their guardian",
	"nobody": "We couldn't find anyone with this number. Please ask a field worker.",
	"switch_person": "Switch person",
	"sign_out": "Sign out",
	# tabs
	"tab_choices": "My choices",
	"tab_history": "History",
	"tab_requests": "Requests",
	# choices
	"agreed_on": "Receipt {0}",
	"needed": "Needed for the service",
	"required": "Required",
	"on": "On",
	"off": "Off",
	"not_asked": "Not asked yet",
	"save_changes": "Save changes",
	"leave_programme": "Leave this programme",
	"left_note": "You have left this programme. To rejoin, please ask a field worker.",
	"confirm_title": "Save your changes?",
	"will_stop": "Stop",
	"will_start": "Start",
	"confirm_note": "Stopping takes effect now. You can change this again at any time.",
	"yes_save": "Yes, save",
	"cancel": "Cancel",
	"saved": "Saved. Your receipt code is {0}.",
	"nothing_changed": "Nothing changed.",
	# leave
	"leave_title": "Leave {0}?",
	"leave_warn": "You will stop getting this programme's services. All these uses stop today:",
	"leave_keep": "We keep a record that you agreed and left, as the law requires, and delete the rest when the retention period ends.",
	"leave_understand": "I understand and want to leave",
	"leave_button": "Leave the programme",
	"go_back": "Go back",
	"left_done": "You have left the programme. Your receipt code is {0}.",
	# history
	"agreed": "Agreed",
	"stopped": "Stopped",
	"said_no": "Said no",
	"left": "Left the programme",
	"download": "Download receipt (PDF)",
	"no_history": "Nothing yet.",
	# requests
	"rights_request": "Rights / support request",
	"rights_request_help": "See, correct or delete your data, stop a use, name someone",
	"raised_by_you": "Raised by you",
	"no_requests": "You haven't asked us anything yet.",
	"we_reply_within": "We reply within {0} days",
	"req_stop": "Stop using some or all of my data",
	"req_stop_help": "Opens My choices: it takes effect at once",
	"req_access": "Show me my data",
	"req_access_help": "A summary of what we hold and why",
	"req_correction": "Correct my details",
	"req_erasure": "Delete my data",
	"req_nomination": "Name someone to act for me",
	"req_nomination_help": "If you die or can't decide for yourself",
	"anything_to_add": "Anything to add? (optional)",
	"hindi_or_english": "Hindi or English",
	"send_request": "Send request",
	"request_sent": "Request {0} sent. We will reply by {1}.",
	"reply_by": "reply by {0}",
	"you": "You",
	"office": "Office",
	"write_to_us": "Write to us",
	"add_more": "Add more details…",
	"send": "Send",
	"st_new_request": "Received",
	"st_who_is_this": "Received",
	"st_working_on_it": "Working on it",
	"st_waiting_for_person": "Waiting for your reply",
	"st_waiting_for_partners": "Waiting for partners",
	"st_request_answered": "Answered",
	"st_request_closed": "Closed",
	"st_cannot_do": "Can't do this",
	"type_access": "Show me my data",
	"type_correction": "Correct my details",
	"type_erasure": "Delete my data",
	"type_nomination": "Name someone to act for me",
	"type_withdrawal": "Stop using my data",
	"type_grievance": "Complaint",
	# general
	"signed_out": "Signed out.",
	"error": "Something went wrong. Please try again.",
	"help": "Need help? Tell any field worker.",
	"dpo": "Data Protection Officer: {0}",
}
