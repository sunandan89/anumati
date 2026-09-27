"""Processor and system routing (spec C7, C6, T15): withdrawals and erasures fan out to whoever holds the
data, and each target's acknowledgement is tracked in a Propagation Ack.

Targets for a purpose are:
  - processors registered for that purpose (Processor › Purposes), and
  - source systems that actually used it for this principal (System Usage Log, from consent.check calls),
  - plus, for retention purges, the systems listed on the retention policy.
A purge with no target is flagged for manual action so a person erases the data and closes it.

Delivery is a signed POST (X-Anumati-Signature: sha256=HMAC(secret, body)) when the target has a URL,
retried with back-off; targets without a URL poll (purge.list, processor.pending). Payloads carry
identifiers and purpose codes only, never names, phone numbers or other personal data."""

import hashlib
import hmac
import json

import frappe
import requests
from frappe.utils import add_days, add_to_date, get_datetime, getdate, now_datetime, today

MAX_ATTEMPTS = 6
OPEN = ("Pending", "Sent", "Acknowledged", "Overdue")
FINAL = ("Completed", "Failed")


def _codes(value):
	return json.loads(value) if isinstance(value, str) else list(value or [])


def _processors_for(purposes: list[str]) -> dict[str, set[str]]:
	"""{processor: purposes it handles, of those given}."""
	out = {}
	for r in frappe.get_all("Processor Purpose", {"parenttype": "Processor", "purpose": ("in", purposes or ["-"])},
	                        ["parent", "purpose"]):
		out.setdefault(r.parent, set()).add(r.purpose)
	return out


def _systems_for(principal: str, purposes: list[str]) -> dict[str, set[str]]:
	"""{source system: purposes it checked for this principal, of those given}."""
	out = {}
	for r in frappe.get_all("System Usage Log", {"principal": principal, "purpose": ("in", purposes or ["-"]),
	                                             "source_system": ("is", "set")}, ["source_system", "purpose"], distinct=True):
		if frappe.db.get_value("Source System", r.source_system, "enabled"):
			out.setdefault(r.source_system, set()).add(r.purpose)
	return out


def _code(purpose):
	return purpose.split("-", 1)[1] if "-" in purpose else purpose


def _ack(reference_doctype, reference_name, principal, purposes, due_on, processor=None, source_system=None):
	key = {"reference_doctype": reference_doctype, "reference_name": reference_name,
	       "processor": processor, "source_system": source_system}
	if (existing := frappe.db.get_value("Propagation Ack", key)):
		return existing
	doc = frappe.get_doc({"doctype": "Propagation Ack", **key, "principal": principal, "status": "Pending",
	                      "purposes": ", ".join(purposes), "due_on": due_on, "next_retry": now_datetime()})
	doc.insert(ignore_permissions=True)
	return doc.name


def _window():
	return frappe.db.get_single_value("Anumati Settings", "propagation_ack_days") or 7


# ------------------------------------------------------------------ fan-out


def on_withdrawal(event):
	"""After a withdrawal event: tell every processor and system that holds the withdrawn purposes."""
	purposes = [f"{event.programme}-{c}" for c in _codes(event.purposes_denied)]
	if not purposes:
		return []
	due = add_days(today(), _window())
	# Each target hears only about the purposes it handles (data minimisation).
	acks = [_ack("Consent Event", event.name, event.principal, sorted(map(_code, held)), due, processor=p)
	        for p, held in sorted(_processors_for(purposes).items())]
	acks += [_ack("Consent Event", event.name, event.principal, sorted(map(_code, used)), due, source_system=s)
	         for s, used in sorted(_systems_for(event.principal, purposes).items()) if s != event.source_system]
	if acks:
		frappe.enqueue("anumati.propagation.deliver_pending", enqueue_after_commit=True)
	return acks


def on_purge_request(purge):
	"""After a Purge Request is opened (erasure right or retention): ask every holder to act."""
	if purge.status == "On Hold" or not purge.purpose:
		return []
	code = frappe.db.get_value("Purpose", purge.purpose, "code")
	systems = set(_systems_for(purge.principal, [purge.purpose]))  # keys: systems that used it
	if purge.retention_policy:
		systems |= set(frappe.get_all("Retention System", {"parenttype": "Retention Policy",
		                                                   "parent": purge.retention_policy}, pluck="source_system"))
	acks = [_ack("Purge Request", purge.name, purge.principal, [code], purge.due_on, processor=p)
	        for p in _processors_for([purge.purpose])]
	acks += [_ack("Purge Request", purge.name, purge.principal, [code], purge.due_on, source_system=s) for s in sorted(systems)]
	if acks:
		frappe.enqueue("anumati.propagation.deliver_pending", enqueue_after_commit=True)
	else:
		purge.db_set("manual_action", 1)
	return acks


# ------------------------------------------------------------------ delivery


def payload(ack) -> dict:
	"""What a processor or system receives. Identifiers and codes only (no personal data)."""
	ref = frappe.get_doc(ack.reference_doctype, ack.reference_name)
	principal_ref = frappe.db.get_value("Data Principal", ack.principal, "principal_ref")
	if ack.reference_doctype == "Purge Request":
		body = {"event": "purge.requested", "action": ref.purge_action,
		        "data_category": ref.data_category, "programme": frappe.db.get_value("Purpose", ref.purpose, "programme")}
	else:
		body = {"event": "consent.withdrawn", "action": "stop_processing", "programme": ref.programme,
		        "consent_id": ref.name, "short_code": ref.short_code}
	return {**body, "request_id": ack.name, "principal_ref": principal_ref,
	        "purposes": [c.strip() for c in (ack.purposes or "").split(",") if c.strip()],
	        "deadline": str(ack.due_on) if ack.due_on else None}


def signature(secret: str, body: bytes) -> str:
	return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _target(ack):
	if ack.processor:
		doc = frappe.get_doc("Processor", ack.processor)
		return doc.webhook_url, doc.get_password("webhook_secret", raise_exception=False)
	doc = frappe.get_doc("Source System", ack.source_system)
	return doc.purge_endpoint, doc.get_password("webhook_secret", raise_exception=False)


def deliver(name):
	"""Push one ack's request to its target, if it has a URL. Failures back off: 5, 10, 20… minutes."""
	ack = frappe.get_doc("Propagation Ack", name)
	if ack.status not in ("Pending", "Overdue"):
		return ack.status
	url, secret = _target(ack)
	if not url:
		return ack.status  # the target polls instead
	body = json.dumps(payload(ack), sort_keys=True, separators=(",", ":")).encode()
	headers = {"Content-Type": "application/json", "X-Anumati-Event": payload(ack)["event"]}
	if secret:
		headers["X-Anumati-Signature"] = signature(secret, body)
	ok = False
	try:
		response = requests.post(url, data=body, headers=headers, timeout=10)
		ok = 200 <= response.status_code < 300
	except requests.RequestException:
		ok = False
	attempts = (ack.attempts or 0) + 1
	if ok:
		ack.update({"status": "Sent", "sent_at": now_datetime(), "attempts": attempts, "next_retry": None})
	elif attempts >= MAX_ATTEMPTS:
		ack.update({"status": "Failed", "attempts": attempts, "next_retry": None,
		            "response": "No successful delivery after %s attempts" % attempts})
	else:
		ack.update({"attempts": attempts, "next_retry": add_to_date(now_datetime(), minutes=5 * 2 ** (attempts - 1))})
	ack.flags.ignore_permissions = True
	ack.save()
	if not ok:
		frappe.log_error(title="Anumati propagation delivery failed", message=f"ack={ack.name} attempt={attempts}")
	return ack.status


def deliver_pending():
	"""Every 10 minutes (and right after a fan-out): push acks that are due for a (re)try."""
	for name in frappe.get_all("Propagation Ack", {"status": ("in", ["Pending", "Overdue"]),
	                                               "next_retry": ("<=", now_datetime())}, pluck="name", limit=500):
		deliver(name)


def mark_overdue():
	"""Daily: acks past their confirm-by date are Overdue (the inbox and partner portal show them)."""
	for name in frappe.get_all("Propagation Ack", {"status": ("in", ["Pending", "Sent", "Acknowledged"]),
	                                               "due_on": ("<", today())}, pluck="name"):
		frappe.db.set_value("Propagation Ack", name, "status", "Overdue")


# ------------------------------------------------------------------ acknowledgements


def record_ack(ack, status, evidence_hash=None, deletion_reference=None, completed_at=None, response=None):
	"""A target says it received (acknowledged), finished (completed) or could not do (failed) the request."""
	status = {"acknowledged": "Acknowledged", "completed": "Completed", "failed": "Failed"}.get(str(status).lower())
	if not status:
		frappe.throw("status must be acknowledged, completed or failed")
	if ack.status in FINAL:
		return ack
	now = now_datetime()
	ack.status = status
	ack.acked_at = ack.acked_at or now
	if status == "Completed":
		ack.completed_at = get_datetime(completed_at) if completed_at else now
	ack.evidence_hash = evidence_hash or ack.evidence_hash
	ack.deletion_reference = deletion_reference or ack.deletion_reference
	if response:
		ack.response = response
	ack.flags.ignore_permissions = True
	ack.save()
	if ack.reference_doctype == "Purge Request":
		settle_purge(ack.reference_name)
	return ack


def settle_purge(purge_request):
	"""A purge is Completed once every target has completed; Acknowledged while some are still working.
	Manual-action purges are completed by a person on the form."""
	acks = frappe.get_all("Propagation Ack", {"reference_doctype": "Purge Request", "reference_name": purge_request},
	                      pluck="status")
	if not acks:
		return
	doc = frappe.get_doc("Purge Request", purge_request)
	if doc.status in ("Completed", "On Hold"):
		return
	if all(s == "Completed" for s in acks):
		doc.update({"status": "Completed", "purged_on": now_datetime()})
	elif any(s in ("Acknowledged", "Completed") for s in acks):
		doc.status = "Acknowledged"
	else:
		return
	doc.flags.ignore_permissions = True
	doc.save()


def caller_source_system(throw=True):
	name = frappe.db.get_value("Source System", {"api_user": frappe.session.user, "enabled": 1})
	if not name and throw:
		frappe.throw("This API user is not registered as an enabled Source System", frappe.PermissionError)
	return name


def caller_processor(throw=True):
	name = frappe.db.get_value("Processor", {"partner_user": frappe.session.user})
	if not name and throw:
		frappe.throw("This user is not the portal user of any processor", frappe.PermissionError)
	return name
