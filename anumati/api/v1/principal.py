"""Principal API, v1: /api/v2/method/anumati.api.v1.principal.<name>

Responses never echo personal data; name and phone go straight into encrypted fields."""

import json

import frappe
from frappe import _

from anumati import profile
from anumati.api import schema

FIELDS = (
	"full_name", "phone", "email", "preferred_language", "persona", "date_of_birth", "age_band",
	"phone_owner_relation", "is_minor", "pwd_guarded", "needs_assistance", "shared_phone", "no_phone", "birth_year",
)


@frappe.whitelist(methods=["POST"])
def upsert(principal_ref, **values):
	"""Create or update a principal by the host system's reference. Idempotent.

	`profile` carries answers to the programme's extra questions ({code: answer}); `programme` says which
	programme asked them."""
	if isinstance(values.get("profile"), str):
		values["profile"] = json.loads(values["profile"] or "{}")
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
	if values.get("profile"):
		profile.save_answers(doc, values.get("programme"), values["profile"])
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
		# The latest guardian's number, so the phone can find a child or guarded adult by it too.
		link = frappe.db.get_value("Guardian Link", {"principal": name}, ["guardian", "relation", "guardian_type"],
		                           as_dict=True, order_by="creation desc")
		guardian_phone = (frappe.get_doc("Data Principal", link.guardian).get_password("phone", raise_exception=False)
		                  if link and link.guardian else None)
		out.append({
			"principal_ref": doc.principal_ref,
			"full_name": doc.get_password("full_name", raise_exception=False) or "",
			"phone": doc.get_password("phone", raise_exception=False) or "",
			"preferred_language": doc.preferred_language,
			**{f: doc.get(f) or 0 for f in FLAGS},
			"last_code": last,
			"guardian_phone": guardian_phone or "",
			"guardian_relation": (link.relation or link.guardian_type or "") if link else "",
			"decisions": [
				{"purpose": frappe.db.get_value("Purpose", s.purpose, "code") or s.purpose, "status": s.status,
				 "at": str(times.get(s.last_event) or s.updated or "")}
				for s in states
			],
		})
	return {"people": out, "until": until, "more": len(rows) >= limit * 10 or len(people) >= limit}


def mask_phone(phone: str | None) -> str:
	"""9876543210 -> 9876543XXX: enough to recognise, not enough to call."""
	digits = "".join(ch for ch in (phone or "") if ch.isdigit())
	if not digits:
		return ""
	keep = max(len(digits) - 3, 0)
	return digits[:keep] + "X" * (len(digits) - keep)


@frappe.whitelist(methods=["GET"])
def reveal(principal):
	"""Name and masked phone for Desk forms. Needs read on the Data Principal; each view goes to the Access
	Log. The full number is never sent to the browser."""
	doc = frappe.get_doc("Data Principal", principal)
	doc.check_permission("read")
	from frappe.core.doctype.access_log.access_log import make_access_log

	make_access_log(doctype="Data Principal", document=doc.name, file_type="name")
	return {"principal_ref": doc.principal_ref,
	        "full_name": doc.get_password("full_name", raise_exception=False) or "",
	        "phone_masked": mask_phone(doc.get_password("phone", raise_exception=False))}


# ---------------------------------------------------------------- Desk search (names stay encrypted)
def match(q: str, limit: int = 50) -> list[str]:
	"""Beneficiary names (record IDs) for a search: a full phone number, a receipt code, a beneficiary ID,
	or whole words of a name (every word must match). Nothing personal is stored or returned in clear."""
	from anumati import inbox, pii

	q = (q or "").strip()
	if not q:
		return []
	perm = {"merged_into": ("is", "not set")}
	digits = pii.normalise_phone(q)
	if len(digits) >= 10 and len(digits) >= len(q.replace(" ", "")) - 3:
		return frappe.get_list("Data Principal", {**perm, "phone_hash": pii.phone_hash(digits)}, pluck="name", limit=limit)
	found = frappe.get_list("Data Principal", {**perm, "principal_ref": q}, pluck="name", limit=limit)
	if found:
		return found
	if q.upper().startswith("AN-") or (len(q) == 6 and q.isalnum() and not q.isalpha()):
		who = inbox.principal_for_short_code(q)
		if who and frappe.has_permission("Data Principal", "read", doc=who):
			return [who]
	words = pii.name_words(q)
	if not words:
		return []
	filters = [["Data Principal", "name_index", "like", f"% {pii.name_token(w)} %"] for w in words]
	filters.append(["Data Principal", "merged_into", "is", "not set"])
	return frappe.get_list("Data Principal", filters=filters, pluck="name", limit=limit, order_by="modified desc")


@frappe.whitelist(methods=["GET"])
def search(q):
	"""Desk: find beneficiaries by whole-word name, full phone number, receipt code or ID.
	Returns record IDs only; the list then shows names through reveal_many (logged)."""
	frappe.has_permission("Data Principal", "read", throw=True)
	return {"principals": match(q)}


@frappe.whitelist(methods=["POST"])
def reveal_many(principals):
	"""Desk list: name and masked phone for the rows on screen (at most 100). Needs read on each record;
	every record shown gets an Access Log entry. The full number never reaches the browser."""
	from frappe.core.doctype.access_log.access_log import make_access_log

	from anumati.api.v1.evidence import STAFF_ROLES

	if not STAFF_ROLES & set(frappe.get_roles()):  # Desk staff only; the field app uses for_device
		raise frappe.PermissionError
	names = frappe.parse_json(principals) if isinstance(principals, str) else principals
	if not isinstance(names, list) or len(names) > 100:
		frappe.throw(_("Send a list of at most 100 beneficiaries."))
	out = {}
	for name in names:
		if not isinstance(name, str) or not frappe.has_permission("Data Principal", "read", doc=name):
			continue
		doc = frappe.get_doc("Data Principal", name)
		make_access_log(doctype="Data Principal", document=doc.name, file_type="list")
		out[name] = {"full_name": doc.get_password("full_name", raise_exception=False) or "",
		             "phone_masked": mask_phone(doc.get_password("phone", raise_exception=False))}
	return out


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def link_query(doctype, txt, searchfield, start, page_len, filters, **kwargs):
	"""Link fields to a Beneficiary (e.g. on a request) search by name, phone, receipt code or ID too.
	Shows the beneficiary ID only, so picking someone does not reveal names."""
	txt = (txt or "").strip()
	or_filters = [["Data Principal", "principal_ref", "like", f"%{txt}%"]]
	hits = match(txt) if len(txt) >= 2 else []
	if hits:
		or_filters.append(["Data Principal", "name", "in", hits])
	return frappe.get_list("Data Principal", filters=filters or {}, or_filters=or_filters,
	                       fields=["name", "principal_ref"], limit_start=start, limit_page_length=page_len,
	                       order_by="modified desc", as_list=True)
