"""Principal API, v1: /api/v2/method/anumati.api.v1.principal.<name>

Responses never echo personal data; name and phone go straight into encrypted fields."""

import frappe
from frappe import _

FIELDS = (
	"full_name", "phone", "email", "preferred_language", "persona", "date_of_birth", "age_band",
	"phone_owner_relation", "is_minor", "pwd_guarded", "needs_assistance", "shared_phone", "no_phone",
)


@frappe.whitelist(methods=["POST"])
def upsert(principal_ref, **values):
	"""Create or update a principal by the host system's reference. Idempotent."""
	if not principal_ref:
		frappe.throw(_("principal_ref is required"))
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
