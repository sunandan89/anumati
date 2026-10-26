"""The conversation between a person and the NGO on a request, shared by Desk (Reply to the person) and the
self-service page (Write to us). Each message is a stock Communication linked to the request, so the Desk
timeline shows the thread with nothing new to learn. Messages are kept as written; phone numbers are never
stored, only the salted hash of the number the person signed in with.

Who moves the status (inbox.py statuses):
  staff "update"   -> Working on it
  staff "question" -> Waiting for the person
  staff "answer"   -> Answered (the answer is also kept on the request)
  person writes    -> Working on it again, if we were waiting for them or had answered"""

import html

import frappe
from frappe import _
from frappe.utils import get_url, now_datetime

from anumati import channels, inbox

KINDS = {"update": inbox.WORKING, "question": inbox.WAITING_PERSON, "answer": inbox.ANSWERED}
MAX_LENGTH = 2000
PAGE = "/my-consent"


def _clean(text) -> str:
	text = (text or "").strip()
	if not text:
		frappe.throw(_("Write a message first."))
	if len(text) > MAX_LENGTH:
		frappe.throw(_("Please keep it under {0} characters.").format(MAX_LENGTH))
	return text


def _add(doc, direction: str, text: str, phone_hash=None):
	comm = frappe.get_doc({
		"doctype": "Communication",
		"communication_type": "Communication",
		"communication_medium": "Other",
		"sent_or_received": direction,
		"subject": _("Message from the person") if direction == "Received" else _("Reply to the person"),
		"content": frappe.utils.escape_html(text),
		"communication_date": now_datetime(),
		"anumati_channel": "web",
		"anumati_sender_hash": phone_hash,
		"reference_doctype": doc.doctype,
		"reference_name": doc.name,
		**({"sender": frappe.session.user} if direction == "Sent" else {}),
	})
	comm.flags.ignore_permissions = True
	comm.insert()
	return comm.name


def staff_message(doc, text: str, kind: str, outcome: str | None = None) -> str:
	"""Staff reply from Desk. Moves the status by `kind` and texts the person that there is a reply. A
	grievance's final answer also records the outcome (grievance.OUTCOME_FOR_PERSON)."""
	from anumati import grievance

	if kind not in KINDS:
		frappe.throw(_("Unknown kind of reply"))
	if not doc.matched_principal:
		frappe.throw(_("Match the request to a person first"))
	if doc.status == inbox.CLOSED:
		frappe.throw(_("This is closed."))
	is_grievance = doc.doctype == "Anumati Grievance"
	if is_grievance and kind == "answer" and outcome not in grievance.OUTCOME_FOR_PERSON:
		frappe.throw(_("Choose the outcome with the final answer."))
	text = _clean(text)
	comm = _add(doc, "Sent", text)
	doc.status = KINDS[kind]
	if kind == "answer":
		doc.answer, doc.answered_on = text, now_datetime()
		if is_grievance:
			doc.outcome = outcome
	doc.save()
	# DLT texts can't carry a free reply, so the SMS only says there is one and where to read it.
	channels.send_sms(doc.matched_principal, "request_reply", {"code": doc.name, "link": get_url(PAGE)},
	                  link=(doc.doctype, doc.name))
	return comm


def person_message(doc, text: str, phone_hash=None) -> str:
	"""The person writes from the self-service page. If we were waiting for them, or had answered, it is
	back with staff."""
	text = _clean(text)
	comm = _add(doc, "Received", text, phone_hash)
	if doc.status in (inbox.WAITING_PERSON, inbox.ANSWERED, inbox.CLOSED):
		doc.status = inbox.WORKING
		doc.flags.ignore_permissions = True
		doc.save()
	return comm


def thread(doctype: str, name: str) -> list[dict]:
	"""The conversation as the person sees it: who wrote, when, and the text (no staff names)."""
	rows = frappe.get_all(
		"Communication",
		{"reference_doctype": doctype, "reference_name": name, "anumati_channel": "web"},
		["sent_or_received", "communication_date", "content"], order_by="communication_date asc, creation asc")
	return [{"from": "you" if r.sent_or_received == "Received" else "office",
	         "at": str(r.communication_date), "text": html.unescape(frappe.utils.strip_html(r.content or "")).strip()} for r in rows]
