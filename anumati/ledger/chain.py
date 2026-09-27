"""Per-tenant hash chains over Consent Event and Audit Entry.

Each tenant is one Frappe site, so each site holds two chains. A record is sealed in its
`before_save` hook: it takes the next sequence number, links to the previous record's hash, and the
tenant key signs its own hash.

    hash = sha256(canonical_json(payload) + prev_hash)

Concurrency: the chain head is read with Frappe's `get_value(..., for_update=True)`, which waits for
any uncommitted insert further up the chain. Unique indexes on `chain_seq` and `hash` make a fork
impossible even if two writers race; the loser gets a duplicate-entry error and can retry.

Admin actions are not hooked: Frappe already records every change in Version (Track Changes) and
every deletion in Deleted Document. `seal_audit_trail` copies new ones into the Audit Entry chain as
hashes, so changing or deleting history afterwards is detectable.
"""

import hashlib
import json

import frappe
from frappe.utils import now_datetime

from anumati.ledger import keystore, signing
from anumati.ledger.canonical import GENESIS_HASH, canonical_json, compute_hash, payload, to_storage

CONSENT_SCHEMA = {
	"event_uuid": "str",
	"chain_seq": "int",
	"key_id": "str",
	"action": "str",
	"principal": "str",
	"programme": "str",
	"notice": "str",
	"notice_version": "str",
	"language": "str",
	"purposes_granted": "json",
	"purposes_denied": "json",
	"capture_mode": "str",
	"channel": "str",
	"captured_by": "str",
	"guardian_link": "str",
	"source_system": "str",
	"witness_digest": "str",
	"evidence": "json",
	"verification_method": "str",
	"verification_status": "str",
	"device_id": "str",
	"device_time": "datetime",
	"server_time": "datetime",
	"ip_address": "str",
	"gps": "str",
}

AUDIT_SCHEMA = {
	"name": "str",
	"chain_seq": "int",
	"key_id": "str",
	"action": "str",
	"ref_doctype": "str",
	"ref_name": "str",
	"actor": "str",
	"logged_at": "datetime",
	"source_doctype": "str",
	"source_name": "str",
	"before_hash": "str",
	"after_hash": "str",
	"remarks": "str",
}

CHAINS = {"Consent Event": CONSENT_SCHEMA, "Audit Entry": AUDIT_SCHEMA}
_UNSEALED = {"name", "chain_seq", "key_id"}

# Stock Frappe doctypes whose history is part of the admin audit trail (access control and config).
STOCK_AUDITED = (
	"User",
	"Role",
	"Role Profile",
	"User Permission",
	"Custom DocPerm",
	"DocShare",
	"Workflow",
	"Webhook",
	"Notification",
	"Social Login Key",
	"System Settings",
)
LEDGERS = tuple(CHAINS)


class ChainError(frappe.ValidationError):
	pass


# ------------------------------------------------------------------ sealing


def check_sealable(doc):
	"""Frappe sanitises markup after before_save; refuse it up front so stored == hashed."""
	for field, kind in CHAINS[doc.doctype].items():
		if field in _UNSEALED or doc.get(field) in (None, ""):
			continue
		value = doc.get(field)
		text = value if isinstance(value, str) else json.dumps(value, default=str)
		if "<" in text or ">" in text:
			frappe.throw(f"{doc.meta.get_label(field)} must not contain < or >", ChainError)


def seal(doc):
	"""Assign chain position, hash and signature to a new ledger record, in place."""
	schema = CHAINS[doc.doctype]
	if doc.doctype == "Consent Event" and not doc.server_time:
		doc.server_time = now_datetime()
	for field, kind in schema.items():  # store exactly what gets hashed
		if field not in _UNSEALED:
			doc.set(field, to_storage(doc.get(field), kind))

	head = frappe.db.get_value(
		doc.doctype,
		{"chain_seq": (">", 0)},
		["chain_seq", "hash"],
		order_by="chain_seq desc",
		for_update=True,
		as_dict=True,
	)
	key_id, private_b64 = keystore.active_key()
	doc.chain_seq = (head.chain_seq + 1) if head else 1
	doc.prev_hash = head.hash if head else GENESIS_HASH
	doc.key_id = key_id
	doc.hash = compute_hash(payload(schema, doc.get), doc.prev_hash)
	doc.signature = signing.sign(private_b64, doc.hash)
	if doc.meta.has_field("short_code"):
		from anumati.api.v1.consent import short_code

		doc.short_code = short_code(doc.hash)


# ------------------------------------------------------------------ admin audit trail


def _digest(obj) -> str | None:
	if obj in (None, "", [], {}):
		return None
	return hashlib.sha256(canonical_json(obj)).hexdigest()


def audited_doctypes() -> list[str]:
	anumati = frappe.get_all("DocType", {"module": "Anumati", "istable": 0}, pluck="name")
	return [dt for dt in anumati if dt not in LEDGERS] + list(STOCK_AUDITED)


def _from_version(v) -> dict:
	data = json.loads(v.data or "{}")
	changed = data.get("changed") or []
	docstatus = next((c for c in changed if c and c[0] == "docstatus"), None)
	if docstatus and docstatus[2] == 1:
		action = "submit"
	elif docstatus and docstatus[2] == 2:
		action = "cancel"
	elif any(data.get(k) for k in ("changed", "added", "removed", "row_changed")):
		action = "update"
	else:
		action = "insert"
	fields = sorted({c[0] for c in changed if c}) + sorted({r[0] for r in (data.get("row_changed") or []) if r})
	return {
		"action": action,
		"ref_doctype": v.ref_doctype,
		"ref_name": v.docname,
		"before_hash": _digest([[c[0], c[1]] for c in changed if c]),
		"after_hash": _digest({k: data.get(k) for k in ("changed", "added", "removed", "row_changed", "data_import") if data.get(k)} or data),
		"remarks": ("Fields: " + ", ".join(fields))[:500] if fields else None,
	}


def _from_deleted(d) -> dict:
	return {
		"action": "delete",
		"ref_doctype": d.deleted_doctype,
		"ref_name": d.deleted_name,
		"before_hash": _digest(json.loads(d.data or "{}")),
		"after_hash": None,
		"remarks": None,
	}


def seal_audit_trail(limit: int = 500) -> int:
	"""Scheduler job: seal new Version and Deleted Document records into the Audit Entry chain."""
	doctypes = audited_doctypes()
	sources = (
		("Version", "ref_doctype", ["name", "ref_doctype", "docname", "data", "owner", "creation"], _from_version),
		("Deleted Document", "deleted_doctype", ["name", "deleted_doctype", "deleted_name", "data", "owner", "creation"], _from_deleted),
	)
	sealed = 0
	for source, dt_field, fields, build in sources:
		last = frappe.get_all(
			"Audit Entry", {"source_doctype": source}, pluck="logged_at", order_by="logged_at desc", limit=1
		)
		cursor = last[0] if last else None
		filters = {dt_field: ("in", doctypes)}
		if cursor:
			filters["creation"] = (">=", cursor)
		rows = frappe.get_all(source, filters=filters, fields=fields, order_by="creation asc, name asc", limit=limit)
		for row in rows:
			if frappe.db.exists("Audit Entry", {"source_name": row.name}):
				continue
			entry = frappe.get_doc(
				{"doctype": "Audit Entry", "source_doctype": source, "source_name": row.name,
				 "actor": row.owner, "logged_at": row.creation, **build(row)}
			)
			entry.flags.ignore_links = True
			entry.insert(ignore_permissions=True)
			sealed += 1
	return sealed


# ------------------------------------------------------------------ verification


def verify_chain(doctype: str, batch_size: int = 1000, anchor: dict | None = None) -> dict:
	"""Walk a chain from genesis and report the first broken link.

	Per row: no sequence gap, prev_hash equals the previous row's hash, the recomputed hash matches,
	and the signature verifies with the key named by key_id. With an anchor ({"seq", "hash"}) from an
	earlier run, also detects truncation. The error names the sequence number, record and reason,
	never field values.
	"""
	schema = CHAINS[doctype]
	keys = keystore.public_keys()
	fields = sorted(set(schema) | {"name", "chain_seq", "prev_hash", "hash", "signature"})
	result = {"ok": True, "doctype": doctype, "checked": 0, "head_seq": 0, "head_hash": GENESIS_HASH, "error": None}
	prev_hash, expected_seq, anchor_seen = GENESIS_HASH, 1, anchor is None

	def fail(row, reason):
		result.update(ok=False, error={"seq": row.get("chain_seq"), "name": row.get("name"), "reason": reason})
		return result

	while True:
		rows = frappe.get_all(
			doctype,
			filters={"chain_seq": (">=", expected_seq)},
			fields=fields,
			order_by="chain_seq asc",
			limit=batch_size,
		)
		if not rows:
			break
		for row in rows:
			if row.chain_seq != expected_seq:
				return fail(row, f"sequence gap: expected {expected_seq}")
			if row.prev_hash != prev_hash:
				return fail(row, "previous-hash link broken")
			if compute_hash(payload(schema, row.get), row.prev_hash) != row.hash:
				return fail(row, "hash mismatch: record changed after sealing")
			public_b64 = keys.get(row.key_id)
			if not public_b64:
				return fail(row, f"unknown signing key {row.key_id}")
			if not signing.verify(public_b64, row.hash, row.signature or ""):
				return fail(row, "signature invalid")
			if anchor and row.chain_seq == anchor.get("seq"):
				if row.hash != anchor.get("hash"):
					return fail(row, "does not match the last verified checkpoint")
				anchor_seen = True
			prev_hash, expected_seq = row.hash, expected_seq + 1
			result["checked"] += 1

	result.update(head_seq=expected_seq - 1, head_hash=prev_hash)
	if not anchor_seen:
		result.update(ok=False, error={"seq": anchor.get("seq"), "name": None, "reason": "chain truncated below the last verified checkpoint"})
	return result


def nightly_verify():
	"""Scheduler job: verify both chains against the last checkpoints; failures go to Error Log."""
	settings = "Anumati Settings"
	summary = []
	for doctype, anchor_field in (("Consent Event", "consent_anchor"), ("Audit Entry", "audit_anchor")):
		raw = frappe.db.get_single_value(settings, anchor_field)
		anchor = json.loads(raw) if raw else None
		res = verify_chain(doctype, anchor=anchor if anchor and anchor.get("seq") else None)
		summary.append(f"{doctype}: {'ok' if res['ok'] else 'FAILED'} ({res['checked']} records)")
		if res["ok"]:
			frappe.db.set_single_value(settings, anchor_field, json.dumps({"seq": res["head_seq"], "hash": res["head_hash"]}))
		else:
			frappe.log_error(title=f"Anumati chain verification failed: {doctype}", message=json.dumps(res["error"]))
	frappe.db.set_single_value(settings, "last_chain_check", now_datetime())
	frappe.db.set_single_value(settings, "last_chain_status", "; ".join(summary))
