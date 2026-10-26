"""Grievances (DPDP Act s.8(10) and s.13): a complaint that something went wrong with a person's data or a
request. Kept apart from rights requests (Rights Request) so routine withdrawals never count as complaints.

Life of a grievance, in the plain statuses of inbox.py:
  Received -> Working on it <-> Waiting for the person -> Answered -> Closed
- Staff reply with Reply to the person (conversation.py); the final answer carries an outcome.
- No final answer after `grievance_dpo_after_days` (15): the DPO gets it (daily job).
- The person says "Yes, this solves it" (Closed) or, once, "No, I'm not happy" (back to Working on it, with
  the DPO). After that, the self-service page shows the route to the Data Protection Board.
- Answered and no word from the person for 30 days: Closed (daily job).
- "Staff behaviour" grievances are seen by the DPO only, so nobody handles a complaint about a colleague."""

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, now_datetime

from anumati import inbox

DPO_ROLES = {"Anumati DPO", "System Manager"}
STAFF_ONLY_DPO = "staff_behaviour"
OPEN = (inbox.NEW, inbox.WHO, inbox.WORKING, inbox.WAITING_PERSON)
AUTO_CLOSE_DAYS = 30
# What the person reads above the final answer (translated when shown).
OUTCOME_FOR_PERSON = {
	"put_right": "You were right. We have put it right.",
	"partly_put_right": "You were partly right. We have put that part right.",
	"no_problem_found": "We checked and found no problem.",
}


# ------------------------------------------------------------------ who
def dpo_user() -> str | None:
	"""The DPO's user: the DPO email in Anumati Settings if it is a user, else the first enabled DPO."""
	email = frappe.db.get_single_value("Anumati Settings", "dpo_email")
	if email and frappe.db.get_value("User", {"name": email, "enabled": 1}):
		return email
	users = frappe.get_all("Has Role", {"role": "Anumati DPO", "parenttype": "User"}, pluck="parent")
	enabled = frappe.get_all("User", {"name": ("in", users or ["-"]), "enabled": 1}, pluck="name", order_by="creation asc")
	return enabled[0] if enabled else None


def to_dpo(doc, why: str):
	"""Give the grievance to the DPO (assigned to, the DPO flag, a note on the timeline)."""
	doc.assigned_to = dpo_user() or doc.assigned_to
	doc.dpo_since = now_datetime()
	doc.add_comment("Info", why)


def _sees_everything(user: str) -> bool:
	return user == "Administrator" or bool(DPO_ROLES & set(frappe.get_roles(user)))


def permission_query_conditions(user=None):
	"""Lists and reports: only the DPO sees staff-behaviour grievances; a field worker sees only those they
	raised."""
	user = user or frappe.session.user
	if _sees_everything(user):
		return ""
	conditions = [f"`tabAnumati Grievance`.`category` != '{STAFF_ONLY_DPO}'"]
	roles = set(frappe.get_roles(user))
	if not roles & {"Anumati Operator", "Anumati Admin"}:
		conditions.append(f"`tabAnumati Grievance`.`owner` = {frappe.db.escape(user)}")
	return " and ".join(conditions)


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if _sees_everything(user):
		return True
	if doc.get("category") == STAFF_ONLY_DPO:
		return False
	roles = set(frappe.get_roles(user))
	if not roles & {"Anumati Operator", "Anumati Admin"} and doc.get("owner") and doc.owner != user:
		return False
	return True


# ------------------------------------------------------------------ new grievances
def create(category: str, channel: str, principal=None, description=None, about_request=None, raised_by_role=None,
           sender_hash=None, raw_payload=None, paper_trail_number=None, raised_by=None, client_request_id=None):
	"""A new grievance from any door (self-service page, field app, SMS, API, a moved request)."""
	doc = frappe.get_doc({
		"doctype": "Anumati Grievance", "category": category, "channel": channel, "matched_principal": principal,
		"description": description, "about_request": about_request, "raised_by_role": raised_by_role,
		"sender_hash": sender_hash, "raw_payload": raw_payload, "paper_trail_number": paper_trail_number,
		"raised_by": raised_by, "received_on": now_datetime(), "client_request_id": client_request_id,
	})
	doc.insert(ignore_permissions=True)
	return doc


def move_from_request(request, ignore_permissions=False):
	"""A rights request that is really a complaint becomes a grievance: same person, dates, text and messages.
	The request is closed with a note."""
	if not ignore_permissions:
		request.check_permission("write")
	doc = frappe.get_doc({
		"doctype": "Anumati Grievance", "category": "something_else", "channel": request.channel,
		"matched_principal": request.matched_principal, "raised_by_role": request.get("raised_by_role"),
		"sender_hash": request.sender_hash, "raw_payload": request.raw_payload, "raised_by": request.raised_by,
		"paper_trail_number": request.paper_trail_number, "received_on": request.received_on,
		"description": request.raw_payload, "assigned_to": request.assigned_to,
	})
	doc.insert(ignore_permissions=True)
	frappe.db.sql("update `tabCommunication` set reference_doctype='Anumati Grievance', reference_name=%s "
	              "where reference_doctype='Anumati Rights Request' and reference_name=%s", (doc.name, request.name))
	doc.add_comment("Info", _("Moved from rights request {0}").format(request.name))
	return doc


def move_to_request(doc, request_type: str):
	"""The reverse: a grievance that is really a rights request."""
	doc.check_permission("write")
	if request_type not in ("withdrawal", "access", "correction", "erasure", "nomination"):
		frappe.throw(_("Choose what they asked for"))
	request = frappe.get_doc({
		"doctype": "Anumati Rights Request", "request_type": request_type, "channel": doc.channel,
		"matched_principal": doc.matched_principal, "raised_by_role": doc.raised_by_role,
		"sender_hash": doc.sender_hash, "raw_payload": doc.raw_payload or doc.description, "raised_by": doc.raised_by,
		"paper_trail_number": doc.paper_trail_number, "received_on": doc.received_on,
	})
	request.insert(ignore_permissions=True)
	frappe.db.sql("update `tabCommunication` set reference_doctype='Anumati Rights Request', reference_name=%s "
	              "where reference_doctype='Anumati Grievance' and reference_name=%s", (request.name, doc.name))
	doc.status = inbox.CLOSED
	doc.internal_note = ((doc.internal_note or "") + "\n" + _("Moved to rights request {0}").format(request.name)).strip()
	doc.save()
	return request


# ------------------------------------------------------------------ the person's answer
def respond(doc, solved: bool):
	"""The person says whether the final answer solved it. "Not happy" works once, within 30 days."""
	if doc.status != inbox.ANSWERED:
		frappe.throw(_("There is no answer to respond to yet."))
	doc.person_said_on = now_datetime()
	if solved:
		doc.person_says, doc.status = "solved", inbox.CLOSED
	else:
		if doc.person_says == "not_happy":
			frappe.throw(_("You have already told us. If you are still not happy, you can complain to the Data Protection Board."))
		doc.person_says, doc.status = "not_happy", inbox.WORKING
		to_dpo(doc, _("The person is not happy with the answer: passed to the DPO."))
	doc.flags.ignore_permissions = True
	doc.save()


def can_say_not_happy(doc) -> bool:
	return (doc.status == inbox.ANSWERED and doc.person_says != "not_happy" and doc.answered_on
	        and doc.answered_on >= add_to_date(now_datetime(), days=-AUTO_CLOSE_DAYS))


# ------------------------------------------------------------------ daily
def daily():
	"""No final answer in time: to the DPO. Answered with no word for 30 days: closed."""
	days = cint(frappe.db.get_single_value("Anumati Settings", "grievance_dpo_after_days")) or 15
	cutoff = add_to_date(now_datetime(), days=-days)
	for name in frappe.get_all("Anumati Grievance", {"status": ("in", OPEN), "dpo_since": ("is", "not set"),
	                                         "received_on": ("<=", cutoff)}, pluck="name"):
		doc = frappe.get_doc("Anumati Grievance", name)
		to_dpo(doc, _("No final answer after {0} days: passed to the DPO.").format(days))
		doc.flags.ignore_permissions = True
		doc.save()
	quiet = add_to_date(now_datetime(), days=-AUTO_CLOSE_DAYS)
	for name in frappe.get_all("Anumati Grievance", {"status": inbox.ANSWERED, "answered_on": ("<=", quiet)}, pluck="name"):
		doc = frappe.get_doc("Anumati Grievance", name)
		doc.status = inbox.CLOSED
		doc.add_comment("Info", _("Closed: no reply from the person {0} days after the answer.").format(AUTO_CLOSE_DAYS))
		doc.flags.ignore_permissions = True
		doc.save()
