"""Writes anumati/public/openapi.json: the published API contract (spec T5).

The same JSON Schemas are used at runtime to validate every write (anumati/api/schema.py), so the docs
and the checks cannot drift. Run from the repo root: python3 tools/gen_openapi.py"""

import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPTURE_MODES = ["self_digital", "self_worker_device", "assisted_verbal", "assisted_thumbprint",
                 "assisted_witnessed", "guardian_minor", "guardian_pwd", "paper"]
METHODS = ["server_otp", "device_sms_otp", "reverse_sms", "missed_call", "deferred", "evidence_only"]
CHANNELS = ["app", "hosted_page", "connector", "field_worker", "slip", "sms", "missed_call", "ivr", "whatsapp",
            "web", "email", "community", "api", "ussd"]
S = lambda **kw: {"type": "string", **kw}
CODES = {"type": "array", "items": S(maxLength=64), "maxItems": 50}
EVIDENCE = {"type": "array", "maxItems": 20, "items": {"type": "object", "additionalProperties": False,
            "required": ["file"], "properties": {"file": S(maxLength=500), "sha256": S(pattern="^[0-9a-f]{64}$"),
                                                 "kind": S(maxLength=40)}}}
CAPTURE = {
	"notice": S(maxLength=140), "language": S(maxLength=10), "capture_mode": S(enum=CAPTURE_MODES),
	"channel": S(enum=CHANNELS), "device_id": S(maxLength=140), "device_time": S(maxLength=40),
	"ip_address": S(maxLength=64), "gps": S(maxLength=64), "verification_method": S(enum=METHODS),
	"witness": S(maxLength=500), "evidence": EVIDENCE, "guardian_link": S(maxLength=140),
	"source_system": S(maxLength=140),
}

SCHEMAS = {
	"ConsentRecord": {
		"type": "object", "additionalProperties": False,
		"required": ["event_uuid", "principal_ref", "programme"],
		"properties": {
			"event_uuid": S(minLength=8, maxLength=64), "principal_ref": S(minLength=1, maxLength=140),
			"programme": S(minLength=1, maxLength=140), "action": S(enum=["grant", "refuse", "renew"]),
			"purposes_granted": CODES, "purposes_denied": CODES,
			"verification_status": S(enum=["recorded", "confirmed", "evidence_only"]), **CAPTURE,
		},
	},
	"ConsentWithdraw": {
		"type": "object", "additionalProperties": False,
		"required": ["event_uuid", "principal_ref", "programme", "channel"],
		"properties": {
			"event_uuid": S(minLength=8, maxLength=64), "principal_ref": S(minLength=1, maxLength=140),
			"programme": S(minLength=1, maxLength=140), "purposes": CODES, **CAPTURE,
		},
	},
	"PrincipalUpsert": {
		"type": "object", "additionalProperties": False, "required": ["principal_ref"],
		"properties": {
			"principal_ref": S(minLength=1, maxLength=140), "full_name": S(maxLength=140), "phone": S(maxLength=20),
			"email": S(maxLength=140), "preferred_language": S(maxLength=10), "persona": S(maxLength=40),
			"date_of_birth": S(maxLength=10), "age_band": S(maxLength=20), "phone_owner_relation": S(maxLength=40),
			**{f: {"enum": [0, 1, True, False, "0", "1"]} for f in
			   ("is_minor", "pwd_guarded", "needs_assistance", "shared_phone", "no_phone")},
		},
	},
	"RightsSubmit": {
		"type": "object", "additionalProperties": False, "required": ["request_type", "channel"],
		"properties": {
			"request_type": S(enum=["withdrawal", "access", "correction", "erasure", "grievance", "nomination"]),
			"channel": S(enum=CHANNELS), "principal_ref": S(maxLength=140), "payload": S(maxLength=5000),
			"paper_trail_number": S(maxLength=140),
		},
	},
	"Artefact": {"type": "object", "properties": {k: S() for k in (
		"consent_id", "short_code", "event_uuid", "action", "hash", "signature", "key_id", "server_time",
		"verification_status")} | {"chain_seq": {"type": "integer"}}},
}


def op(summary, body=None, query=None, public=False, method="post"):
	o = {"summary": summary, "responses": {"200": {"description": "OK"}, "401": {"description": "Not authenticated"},
	                                        "403": {"description": "Not permitted"}}}
	if body:
		o["requestBody"] = {"required": True, "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{body}"}}}}
	if query:
		o["parameters"] = [{"name": n, "in": "query", "required": r, "schema": {"type": "string"}} for n, r in query]
	if public:
		o["security"] = []
	return {method: o}


BASE = "/api/v2/method/anumati.api.v1."
PATHS = {
	BASE + "consent.record": op("Record a grant, refusal or renewal; returns the signed artefact",
	                            body="ConsentRecord") | {"x-body-wrapper": "event"},
	BASE + "consent.withdraw": op("Withdraw consent (default: every optional purpose granted)", body="ConsentWithdraw"),
	BASE + "consent.check": op("Enforcement gate", query=[("principal_ref", True), ("purpose", True), ("programme", False)], method="get"),
	BASE + "consent.state": op("Every purpose's state for one principal", query=[("principal_ref", True), ("programme", False)], method="get"),
	BASE + "consent.verify": op("Verify an artefact (public)", query=[("hash", True), ("signature", False)], public=True, method="get"),
	BASE + "consent.public_keys": op("Tenant signing public keys (public)", public=True, method="get"),
	BASE + "principal.upsert": op("Create or update a principal", body="PrincipalUpsert"),
	BASE + "notice.get_active": op("Live notice for a programme", query=[("programme", True), ("language", False)], method="get"),
	BASE + "rights.submit": op("Submit a rights request", body="RightsSubmit"),
	BASE + "rights.fulfil_withdrawal": op("Carry out a withdrawal request (staff)", query=[("request", True), ("programme", True)]),
	BASE + "rights.send_summary": op("Access: send a summary of what is held (staff)", query=[("request", True)]),
	BASE + "rights.mark_corrected": op("Correction: close with the changed field names (staff)", query=[("request", True)]),
	BASE + "rights.start_erasure": op("Erasure: withdraw optional purposes and open purge requests (staff)",
	                                  query=[("request", True), ("programme", False)]),
	BASE + "rights.add_nominee": op("Nomination: record a nominee, encrypted (staff)",
	                                query=[("request", True), ("nominee_name", True), ("relation", True), ("contact", False)]),
	BASE + "rights.close": op("Close or reject a request and tell the principal (staff)",
	                          query=[("request", True), ("resolution", False), ("status", False)]),
	BASE + "rights.reply": op("Reply on the thread with an approved template (staff)",
	                          query=[("request", True), ("template_event", False)]),
	BASE + "rights.fulfil": op("A host system confirms it carried out a rights request (Source System user)",
	                           query=[("request", True), ("result", True), ("evidence_hash", False)]),
	BASE + "purge.list": op("Open purge requests for the calling Source System (T15)", query=[("limit", False)], method="get"),
	BASE + "purge.ack": op("Acknowledge or complete a purge request with an evidence hash (T15)",
	                       query=[("request_id", True), ("status", True), ("evidence_hash", False), ("completed_at", False)]),
	BASE + "processor.pending": op("Withdrawals and erasures routed to the calling processor partner", method="get"),
	BASE + "processor.confirm": op("Partner confirms action with an evidence hash or deletion reference",
	                               query=[("request_id", True), ("evidence_hash", False), ("deletion_reference", False), ("status", False)]),
	BASE + "notifications.feed": op("Polling feed mirroring webhooks", query=[("since", True), ("limit", False)], method="get"),
	BASE + "verification.send_otp": op("Send a one-time code for a consent event (server OTP)", query=[("consent_id", True)]),
	BASE + "verification.verify_otp": op("Check the code; confirms the consent", query=[("consent_id", True), ("code", True)]),
	BASE + "channel.inbound_sms": op("SMS gateway callback: keywords STOP / STOP <code> / STOP <n> / DATA / HELP",
	                                query=[("provider", True), ("token", True), ("sender", True), ("message", True)], public=True),
	BASE + "channel.missed_call": op("Missed-call callback: opens a withdrawal request",
	                                query=[("provider", True), ("token", True), ("caller", True)], public=True),
	BASE + "channel.delivery_report": op("Delivery receipt callback: confirms deferred confirmations",
	                                    query=[("provider", True), ("token", True), ("request_id", True), ("status", True)], public=True),
	BASE + "channel.inbound_whatsapp": op("Twilio WhatsApp webhook: STOP menu, replies in TwiML (signed by Twilio)",
	                                     query=[("provider", True), ("token", True)], public=True),
	BASE + "channel.ivr": op("Twilio voice webhook: keypad menu, press 1 to withdraw (signed by Twilio)",
	                        query=[("provider", True), ("token", True)], public=True),
	BASE + "chain.verify": op("Verify a ledger chain (DPO/Admin)", query=[("ledger", False)], method="get"),
}

doc = {
	"openapi": "3.1.0",
	"info": {"title": "Anumati API", "version": "1", "license": {"name": "AGPL-3.0"},
	         "description": "Open-source DPDP consent API. Auth: `Authorization: token <api_key>:<api_secret>`. "
	                        "Scopes are the API user's Frappe roles. Writes are idempotent on event_uuid."},
	"servers": [{"url": "https://{tenant}", "variables": {"tenant": {"default": "anumati.nvi.frappe.cloud"}}}],
	"components": {"schemas": SCHEMAS,
	               "securitySchemes": {"token": {"type": "apiKey", "in": "header", "name": "Authorization"}}},
	"security": [{"token": []}],
	"paths": PATHS,
}
out = os.path.join(REPO, "anumati", "public", "openapi.json")
with open(out, "w") as fh:
	json.dump(doc, fh, indent=1, sort_keys=True)
	fh.write("\n")
print("wrote", os.path.relpath(out, REPO))
