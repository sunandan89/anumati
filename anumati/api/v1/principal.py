"""Principal API, v1: /api/v2/method/anumati.api.v1.principal.<name>

Responses never echo personal data; name and phone go straight into encrypted fields."""

import frappe
from frappe import _

from anumati.api import schema

FIELDS = (
	"full_name", "phone", "email", "preferred_language", "persona", "date_of_birth", "age_band",
	"phone_owner_relation", "is_minor", "pwd_guarded", "needs_assistance", "shared_phone", "no_phone",
)


@frappe.whitelist(methods=["POST"])
def upsert(principal_ref, **values):
	"""Create or update a principal by the host system's reference. Idempotent."""
	schema.validate("PrincipalUpsert", {"principal_ref": principal_ref,
	                                    **{k: v for k, v in values.items() if k not in ("cmd", "data") and v is not None}})
	name = frappe.db.get_value("Data Principal", {"principal_ref": principal_ref})
	if name:
		doc = frappe.get_doc("Data Principal", name)
		doc.check_permission("write")
	else:
		frappe.has_permission("Data Principal", "create", throw=True)
		doc = frappe.new_doc("Data Principal")
		doc.principal_ref = principal_ref
	doc.update({k: values[k] for k in FIELDS if k in values})
	doc.save()
	frappe.cache.delete_value(f"anumati:principal:{principal_ref}")
	return {"principal_ref": doc.principal_ref, "created": not name}


FLAGS = ("is_minor", "pwd_guarded", "needs_assistance", "shared_phone", "no_phone")


@frappe.whitelist(methods=["GET"])
def for_device(programme, since=None, limit=500):
	"""People in a programme with their current choices, for a field worker's phone (spec A5, offline find,
	withdrawal and add-a-purpose). The phone stores them in its encrypted database.

	Needs read on Data Principal and on this Programme (User Permissions apply). Pages by the time a
	person's consent state last changed: pass `until` back as `since`. Personal data goes only to the
	signed-in worker's device over HTTPS and is never logged."""
	frappe.has_permission("Data Principal", "read", throw=True)
	if not frappe.db.exists("Programme", programme):
		frappe.throw(_("Unknown programme {0}").format(programme), frappe.DoesNotExistError)
	frappe.get_doc("Programme", programme).check_permission("read")
	limit = min(int(limit or 500), 1000)

	filters = {"programme": programme}
	if since:
		filters["updated"] = (">", since)
	rows = frappe.get_all("Consent State", filters, ["principal", "purpose", "status", "last_event", "updated"],
	                      order_by="updated asc", limit_page_length=limit * 10)
	people: dict[str, list] = {}
	until = since
	for r in rows:
		if r.principal not in people and len(people) >= limit:
			break
		people.setdefault(r.principal, []).append(r)
		until = str(r.updated) if r.updated else until

	out = []
	for name, states in people.items():
		doc = frappe.get_doc("Data Principal", name)
		if doc.merged_into:
			continue
		events = {s.last_event for s in states if s.last_event}
		times = dict(frappe.get_all("Consent Event", {"name": ("in", list(events))}, ["name", "device_time"],
		                            as_list=True)) if events else {}
		last = frappe.db.get_value("Consent Event", {"principal": name, "programme": programme},
		                           "short_code", order_by="creation desc")
		out.append({
			"principal_ref": doc.principal_ref,
			"full_name": doc.get_password("full_name", raise_exception=False) or "",
			"phone": doc.get_password("phone", raise_exception=False) or "",
			"preferred_language": doc.preferred_language,
			**{f: doc.get(f) or 0 for f in FLAGS},
			"last_code": last,
			"decisions": [
				{"purpose": frappe.db.get_value("Purpose", s.purpose, "code") or s.purpose, "status": s.status,
				 "at": str(times.get(s.last_event) or s.updated or "")}
				for s in states
			],
		})
	return {"people": out, "until": until, "more": len(rows) >= limit * 10 or len(people) >= limit}
