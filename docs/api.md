# Anumati API v1

Base: `https://<tenant>/api/v2/method/anumati.api.v1.<module>.<method>` (the `/api/method/…` form also works).
Auth: `Authorization: token <api_key>:<api_secret>` of a Frappe user. There's no separate scope system; the user's roles are the scope (spec gap 10):

| Scope | Needs | Roles that have it |
|---|---|---|
| capture | create on Consent Event | Anumati Field Worker, System Manager |
| check | read on Consent State | Field Worker, Developer, Operator, Programme Manager, DPO, Admin |
| principal | create/write on Data Principal | Field Worker, Operator, DPO, Admin |

For a connector or host app, create a User with the right role, generate its API key on the User form, and register it as a **Source System** (its `check` calls then land in System Usage Log).

## consent.record (POST)
```json
{"event": {"event_uuid": "c0a8…", "principal_ref": "MHU-004211", "programme": "MHU",
  "purposes_granted": ["screen", "follow"], "purposes_denied": ["research"],
  "notice": "MHU-v4.0.0", "language": "hi", "capture_mode": "assisted_thumbprint", "channel": "app",
  "device_id": "FW-104", "device_time": "2026-09-20 11:20:00", "verification_method": "device_sms_otp",
  "verification_status": "recorded", "witness": "…", "evidence": [{"file": "…", "sha256": "…"}]}}
```
Returns the signed artefact `{consent_id, event_uuid, action, chain_seq, hash, signature, key_id, server_time, verification_status}`. Replaying the same `event_uuid` returns the original artefact. Rules: purposes must belong to the programme; a child needs a `guardian_link` for that child and can't be granted purposes marked "not for minors"; a guardian other than a parent needs the order number (`authority_ref`) on the link; an adult who can't decide alone (`pwd_guarded`) needs a guardian appointed by a court or the Local Level Committee (`committee`, `court` or `legal_guardian`) with the order number; someone who needs help reading (`needs_assistance`) needs a `witness` when they agree; a child who has turned 18 consents for themself (no guardian), which makes them an adult record; `action` is grant | refuse | renew.

The server, not the caller, sets `verification_status`: whatever is sent, a new consent is `recorded`, or `evidence_only` when `verification_method` is `evidence_only` and at least one evidence item checks out (or the guardian link carries the order or ID). It becomes `confirmed` only through `verification.verify_otp` or a delivery report. Each `evidence` item must name a private file uploaded for this person (or their guardian link) and the `sha256` of its original bytes; anything else is refused. Decisions are ordered by `device_time`, capped at the time the server received them.

## Consent Event by standard insert (Frappe Mobile SDK, REST)
A Consent Event can also be created as a plain record: `POST /api/resource/Consent Event`, `frappe.client.insert`, or the Frappe Mobile SDK's own sync. The same rules run whichever way it arrives, because they live in the record itself (`anumati.consent_rules`): purposes, who may consent, the notice, evidence, and the server-set fields. Send `principal` (the Data Principal's name), `programme`, `action` (grant, refuse, renew or withdraw), `purposes_granted` / `purposes_denied`, and either `event_uuid` or the SDK's `mobile_uuid` (it becomes the event's ID and receipt code). Whatever is sent for `verification_status`, `server_time`, the chain fields, `short_code`, `notice_version`, `witness_digest` or `captured_by` is replaced by the server. Evidence uploaded beforehand and not attached to anything counts when the same user uploaded it; it is then attached to the person and encrypted.

## consent.withdraw (POST)
`principal_ref, programme, channel, event_uuid, purposes?, paper_trail_number?, leave_programme?` plus any capture fields. With no `purposes`, it withdraws every optional purpose currently granted (spec section 6). Idempotent on `event_uuid`. With `channel` `field_worker` or `slip`, it also files one **Closed** withdrawal Rights Request linked to the event, carrying the slip number, so the inbox lists every withdrawal. `leave_programme` (with no `purposes`) withdraws every purpose of the programme, essential ones and those already off included (so an older grant synced later cannot turn one back on), and marks the person's relationship ended once nothing is granted in any programme. A newer grant of an essential purpose clears it; an older one arriving late does not.

## consent.check (GET)
`principal_ref, purpose, programme?` returns `{allow, status, event, principal_ref, purpose, checked_at}`. It is served from Redis. `status` is one of granted | withdrawn | refused | not_asked | unknown_principal | awaiting_confirmation. A grant that isn't confirmed yet is denied for minors, and for programmes with *Allow processing before confirmation* off.

## consent.state (GET)
`principal_ref, programme?` returns every purpose's `{purpose, status, verification_status, event}`.

## consent.verify, consent.public_keys (GET, public)
Verify an artefact's hash and signature without seeing personal data. `public_keys` lists this tenant's signing keys.

## principal.upsert (POST)
`principal_ref` plus any of `full_name, phone, email, preferred_language, persona, date_of_birth, birth_year, age_band, phone_owner_relation, is_minor, pwd_guarded, needs_assistance, shared_phone, no_phone`, and `profile` (answers to the programme's extra questions, `{code: answer}`; a choice is stored as its English value) with `programme`. A `birth_year` or `date_of_birth` sets the day the person turns 18; from then `consent.check` answers `renewal_due` until they consent themselves. Returns `{principal_ref, created}` and never echoes personal data.

## principal.for_device (GET)
`programme, since?, limit?` returns `{people: [...], until, more}` for a field worker's phone: each person's `principal_ref`, name, phone, language, segment flags, `last_code`, `guardian_phone` and `guardian_relation` (from their latest Guardian Link, so the phone can find a child by the parent's number), and `decisions`. Pages by when a person's consent state last changed; pass `until` back as `since`. Personal data goes only to the signed-in worker's device over HTTPS and is never logged.

## notice.get_active (GET)
`programme, language?` returns the live notice with its purposes (each with `needs_phone`: not offered to someone without a phone), Rule 3 contents and cross-border line, and `profile_questions`: the extra questions the programme switched on and the notice mentions, in the requested language (`code, question, answer_type, options [{value, label}], required, sensitive`). `server_codes` says whether the server can text one-time codes now (an SMS account with a key and an approved OTP template); when false, the field app sends codes from the worker's phone with the voice "haan". A reviewed translation carries `purposes`: the uses' names and descriptions in that language. The translation is included only if a reviewer signed it off; machine-made audio is only served once reviewed.

## verification.send_otp, verification.verify_otp (POST)
`consent_id` sends a 6-digit code from the server to the person's phone (or their guardian's), through the SMS provider, so the field worker never sees it; `consent_id, code` checks the code the person reads back and marks the consent `confirmed`. Only the worker who captured the consent, or staff, may call them. The code is kept only as a hash for 10 minutes; 5 wrong tries lock it; at most 3 codes per consent per 10 minutes. `send_otp` returns `{sent: false, reason: "not_set_up"}` when no provider, approved OTP template or phone is set, so the app falls back to confirm-later. With MSG91, an OTP Message Template set to **Send via: SendOTP** uses an approved SendOTP template (e.g. `Your OTP is ##OTP##`); Anumati still makes and checks the code. A code sent from the worker's own phone (`device_sms_otp`) is recorded but never counts as `confirmed`, and `consent.record` refuses it without the recorded voice "haan" (an `audio` evidence item). Each programme chooses **How SMS codes are sent**: *MSG91 when online* (the app falls back to the worker's phone plus voice when offline) or *Worker's phone*.

## notifications.guardian_needed (POST)
`programme` tells the programme's coordinators (Programme Managers) in their Desk notifications that a field worker met an adult who can't decide alone and has no lawful guardian yet, so no consent was taken. Carries no personal data. With `client_request_id`, a retry within 30 days tells nobody again.

## Messages to guardians
Receipts, confirmation requests and withdrawal confirmations for a child, or an adult with a lawful guardian, go to the guardian's phone (from the latest Guardian Link). "STOP" or a missed call from a guardian's phone also finds the people they consented for.

## rights.submit (POST)
`request_type` (withdrawal | access | correction | erasure | grievance | nomination), `channel`, `principal_ref?`, `payload?`, `paper_trail_number?`, `consent_code?` returns `{request, status, sla_due}`. The SLA clock starts at receipt. Without `principal_ref`, a receipt code (`AN-7K2Q4C` or `7K2Q4C`) in `consent_code` matches the person when it is unambiguous. `client_request_id` (a UUID made once per request, as `grievance.submit` also takes) makes a retry return the first request instead of filing a second one.

## device.register / device.sign_out (POST, field workers)
`device_id` checks a phone in on sign-in and every sync, or frees it on sign-out. Only users with the Field Worker role may call them, and a phone stays with the worker signed in on it until they sign out or a coordinator sets its status to `logged_out`; anyone else is refused.

## Rights Request and Grievance by standard insert
Field workers and connected systems can also create these as plain records (REST or the Frappe Mobile SDK). Only what the person or worker says is kept: the request type or category, channel, who it is about, their words and any paper-trail number. Status, received time, reply-by date, assignment, answer, outcome and the person's response are set by the server and staff (`anumati.intake`). The SDK's `mobile_uuid` becomes `client_request_id`, so the same record pushed twice is refused the second time.

## rights.fulfil_withdrawal (POST, staff)
`request, programme, purposes?, leave_programme?` records one signed withdrawal for a matched request and closes it. An essential purpose in `purposes` without `leave_programme` is refused: it stops only when the person leaves. Calling it twice returns the same event. In Desk this is the **Record withdrawal** button on the request.

## rights.withdrawable (GET, staff)
`request` returns the uses currently on for the request's person: `[{programme, programme_name, code, title, essential}]`. It feeds the Record withdrawal checklist and carries no personal data.

## grievance.submit (POST)
`category` (used_without_consent | did_not_stop | wrong_details | shared_or_leaked | staff_behaviour | request_not_answered | something_else), `channel`, `principal_ref?`, `description?`, `about_request?`, `consent_code?`, `paper_trail_number?` returns `{grievance, status, sla_due}`. A grievance is a complaint and is kept apart from rights requests, so routine requests never count as complaints. Without `principal_ref`, a receipt code in `consent_code` matches the person when it is unambiguous. With no final answer after 15 days (**Anumati Settings → grievance_dpo_after_days**) it goes to the DPO; answered with no word from the person for 30 days, it closes. *Staff behaviour* grievances are seen by the DPO only. Needs Grievance create permission (field worker, operator, DPO).

## grievance.reply, grievance.move_from_request, grievance.move_to_request (POST, staff)
`grievance, message, kind?` (update | question | answer), `outcome?` (put_right | partly_put_right | no_problem_found, with `answer`) replies to the person. `move_from_request` turns a rights request that is really a complaint into a grievance and closes the request; `move_to_request` (`grievance_name, request_type`) does the reverse.

## notifications.feed (GET)
`since` (ISO datetime), `limit?` (at most 500) returns `{events: [...], until}`. It mirrors the webhook events (`consent.recorded`, `consent.withdrawn`, `rights.created`, `rights.closed`) for hosts that can't receive webhooks. Pass `until` back as the next `since`. It carries identifiers and purpose codes only.

## chain.verify (GET, DPO/Admin)
`ledger` = Consent Event | Audit Entry. Walks the chain and reports the first broken link.

Out-of-order sync: a purpose's state only changes when an event is newer than the one that last set it (device time, then server time). Consent State can be rebuilt from the ledger at any time (`anumati.enforcement.rebuild`).

## Contract and validation
The machine-readable spec is at `https://<tenant>/assets/anumati/openapi.json`, generated by `tools/gen_openapi.py`. Every write is checked against the same JSON Schemas. Unknown fields and bad values are rejected with the field name only; the value is never echoed back.

## Webhooks (stock Frappe, no code)
To push events to a host system: **Webhook → New**.
- **Document type** `Consent Event`, **Doc event** `after_insert`, **Request URL** = your endpoint.
- **Condition** `doc.action == "withdraw"` for `consent.withdrawn`, or leave it empty for every event.
- **Webhook data:** pick fields such as `name`, `short_code`, `action`, `programme`, `purposes_granted`, `purposes_denied`, `server_time`. Never pick witness or evidence fields.
- **Webhook secret:** Frappe signs each request (`X-Frappe-Webhook-Signature`, HMAC-SHA256). Failed deliveries show in **Webhook Request Log**.

## Connecting a host system (stock Frappe)
1. **User → New** (e.g. `odk@yourorg`). Give it only the role it needs: **Anumati Field Worker** for capture, **Anumati Developer** for check only. Save.
2. On that user, **Settings → API Access → Generate Keys**. The secret is shown once. Store it in the host system's secret store, never in email or chat.
3. **Source System → New**: the name, type (ODK, CommCare…) and API user. Its `check` calls then land in System Usage Log, which later routes purge requests only to systems that used the data.
