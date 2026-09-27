# Phase 2 — Rights and channels: build plan

Spec: `docs/anumati-spec-v0.4.md` §11 (Phase 2), with §4 (B3, B4, B5, C1–C4, C6, C7), §5, §6, §7, §8 and §10. Look and copy come from `docs/anumati-prototype.html` (Beneficiary touchpoints, Console › Inbox / Campaigns / Audit & governance, Analytics, Auditor & partners › Partner confirmations).

Same rule as Phase 0: **use what Frappe already does, configure it, write code only where Frappe has nothing.**

## 0. Where Phase 1 left us

| Done on `main` | Still outside this repo |
|---|---|
| Consent API (record, withdraw, check, state, verify), principal upsert, active notice (1a) | Anumati Collect screens M1–M8 (`anumati_collect`) |
| Notice builder, Rule 3 checklist, publish gate (1b) | ODK connector (`anumati_connectors`) |
| SMS via MSG91, server OTP, deferred confirmation, inbound STOP / DATA / HELP, missed call (1c) | Pilot: 500 real consents |
| Rights inbox: SLA clock, shared-number matching, withdrawal fulfilment, printed receipt (1d) | |
| OpenAPI contract + schema validation, polling feed (1e) | |
| Console workspace, "Relationship ended" (1f) | |

The Phase 1 exit gate (pilot) depends on the two other repos. Phase 2 server work doesn't, so it starts now; the pilot runs in parallel.

## 1. Scope and exit gate

Spec §11: WhatsApp bot, IVR, email, preference centre, rights requests with SLA, guardian flows (C1, C2), processor routing, retention + purge, true-up campaigns, Frappe/mGrant client. Surfaces: WhatsApp and IVR, preference centre, hosted page, campaigns, analytics.

**Exit gate:** every consensus Must met in the pilot NGO. The Musts Phase 2 closes or finishes:

| Must | What Phase 2 adds |
|---|---|
| B3 Versioning + re-consent | Re-consent campaign on material notice change |
| B4 Withdrawal + preference centre | WhatsApp menu, IVR, email, web preference centre, community point |
| B5 Rights workflow | Access, correction, erasure, grievance, nomination fulfilled end to end, with SLA and thread |
| C6 Retention + erasure | Retention engine, advance notice, purge lifecycle with acknowledgements |
| A6 Language across the journey | Every new channel replies in `preferred_language` |
| C5 Security | Every new guest route is signed, rate-limited and on the allowlist |

Also in scope (P1): C1/C2 guardian flows, C3 true-up, C4 refusal + legal hold, C7 processor routing.

## 2. Capability map — need → Frappe feature

| Need | Frappe feature | Code? |
|---|---|---|
| Rights request assignment, reminders, overdue | Assign To, Assignment Rule, Notification (Days After) | No (fixtures) |
| Conversation thread per request (T4) | Communication + timeline (Phase 0 custom fields) | Small: reply sends via gateway |
| Staff replies only with approved templates | Message Template (`approved`) | Small |
| Processor webhooks with HMAC + delivery log | Stock Webhook for Desk-configured hosts; **our own signed POST** for per-processor fan-out (needs per-row ack tracking) | Yes `anumati/propagation.py` |
| Retention clocks, nightly purge | `scheduler_events` daily | Yes `anumati/retention.py` |
| Campaign import | Data Import (CSV → Data Principal) | No |
| Campaign sends in batches | `frappe.enqueue` + RQ | Yes `anumati/campaigns.py` |
| Preference centre, hosted consent page | Website route (`www/` Jinja + vanilla JS), PWA manifest | Yes (pages + one API) |
| Web OTP login | Our Redis OTP (Phase 1c), no Frappe user for principals | Small |
| WhatsApp / IVR / email providers | Channel Provider DocType (Phase 0), adapters | Yes `anumati/channels/*` |
| Inbound email | Stock Email Account → Communication → Rights Request (Phase 1d) | Small: match on receipt code |
| Analytics | Query Report + Dashboard Chart + Number Card; one custom Page for the prototype layout | Mostly config; one page |
| Partner confirmations | Portal page over `processor.pending / confirm` | Phase 3 UI; API now |

## 3. Slices

Each slice is one commit (like 1a–1f), tests first, CI green before the next.

| # | Slice | Spec | Depends on | Est. |
|---|---|---|---|---|
| **2a** | **Rights fulfilment**: access (data summary), correction, erasure (→ purge), grievance (Board route), nomination; overdue status; reply from thread; `rights.fulfil`; `rights.closed` in feed; Assignment Rule + overdue Notification fixtures | B5, T4, §6 | — | 1 wk |
| **2b** | **Processor routing + purge lifecycle**: fan-out on withdrawal and erasure to processors (by purpose) and source systems (by System Usage Log); signed POST, retries, Propagation Ack; `purge.list / purge.ack` (T15 names); `processor.pending / confirm` with evidence hash; manual DPO task when no system is linked | C7, C6, T15 | 2a | 1 wk |
| **2c** | **Retention engine**: nightly job over Retention Policy (start = collection / withdrawal / relationship ended), advance notice, Purge Requests, action at expiry (erase / anonymise / ask processor / legal hold → review); consent-record retention kept separate; refusal outcome + legal hold (C4) | C6, C4, T1, T16 | 2b | 1 wk |
| **2d** | **Guardian flows**: Guardian Link rules (minor needs verified guardian; court/committee need authority ref + order), `principal.link_guardian`, guardian OTP to the guardian's phone, turning-18 job (flag, majority-transfer campaign, guardian consent lapses after grace) | C1, C2, gap 14 | — | 1 wk |
| **2e** | **WhatsApp**: generic adapter interface; Gupshup adapter (Glific second); outbound receipts/confirmations as approved templates; inbound STOP → menu (all optional / one purpose / erase / see my data), "who is this for?" on shared numbers; session state in Redis with TTL | B4, §6 | 2a | 1 wk |
| **2f** | **IVR + call-back**: Exotel adapter; language menu, press 1 to withdraw, DTMF confirmation, recording reference; call-back for shared-number missed calls ("press 1 for …" by position, never by name); IVR prompts from Message Template (channel = ivr) | B4, §6 | 2e | 1 wk |
| **2g** | **Email**: outbound receipts/confirmations via stock Email Account; inbound replies matched by receipt code or sender, else review queue | B4 | 2a | 2 d |
| **2h** | **Preference centre**: `/consent/choices` page; login by receipt code + OTP (or phone + OTP), code + DOB fallback; per-purpose toggles write signed events (channel = web); rights tiles open requests; language switch; WCAG (T9) | B4, B5, A6 | 2a | 1 wk |
| **2i** | **Hosted consent page**: `session.create(programme, principal_ref, return_url)` returns a one-time URL; notice, equal-weight Accept all / Decline optional, OTP, minor → guardian step; redirects back with `consent_id`; `principal.link(temp_ref, principal_ref)` | A2–A4, gap 1, §8 | 2h | 1 wk |
| **2j** | **Campaigns**: Campaign Member DocType (per-person status); audience from Data Import / programme filter; send via chosen channels in batches; opt-in by YES reply, missed call, web or field visit; refusal and no-response → fallback outcome at deadline; auto triggers (material notice change, turning 18, validity expiry, retention notice) | C3, B3, gaps 14, 17 | 2c–2e | 1.5 wk |
| **2k** | **Analytics**: aggregate queries for Overview, Verification, Withdrawals & rights, Languages & districts, Field team; counts each principal's latest state (T18); no personal data; one Frappe page with the prototype layout | §3a metrics, C8 | 2a, 2j | 1 wk |
| 2l | **`anumati_client`** (Frappe/mGrant): Link field + `before_insert` enforcement hook calling `consent.check` | §8 connectors | API stable | separate repo |

Critical path: 2a → 2b → 2c → 2j. Channels (2e–2g) and web (2h–2i) can run alongside once 2a lands.

## 4. Data model changes

Kept small; most DocTypes exist since Phase 0.

| DocType | Change | Slice |
|---|---|---|
| Rights Request | `+ programme`, `+ correction_fields` (field names only, values go through the encrypted principal form), `+ overdue` (check, set daily), `+ board_route_shown`, `+ closed_on` | 2a |
| Propagation Ack | `+ attempts`, `+ next_retry`, `+ rights_request`, `+ consent_event` shortcuts for list filters | 2b |
| Purge Request | `+ source_system`, `+ evidence_hash`, `+ completed_on`, `+ batch` | 2b |
| Anumati Settings | `+ board_complaint_url`, `+ guardian_grace_days` (default 30), `+ purge_batch_limit` | 2a, 2d |
| Guardian Link | `+ status` (pending / verified / lapsed), `+ lapsed_on` | 2d |
| **Campaign Member** (new) | campaign, principal, status (queued / sent / opted_in / refused / no_response / fallback_applied), channel, sent_at, responded_at, consent_event | 2j |
| **Channel Session** (not a DocType) | WhatsApp / IVR / web menu state in Redis with TTL | 2e–2h |
| Message Template | events `+ access_summary`, `campaign_invite`, `ivr_menu`, `guardian_otp` | 2a, 2d, 2e, 2j |

## 5. New API surface

| Method | Auth | Slice |
|---|---|---|
| `rights.fulfil(request, system?, result, evidence_hash?)` | staff / host system | 2a |
| `purge.list(limit?)`, `purge.ack(request, status, evidence_hash, completed_at)` | Source System API user | 2b |
| `processor.pending()`, `processor.confirm(ack, evidence_hash?, deletion_reference?)` | Processor Partner | 2b |
| `principal.link_guardian(principal_ref, guardian_ref, guardian_type, …)` | capture | 2d |
| `channel.inbound_whatsapp`, `channel.ivr` | guest + provider secret, rate-limited, allowlisted | 2e, 2f |
| `portal.request_otp`, `portal.login`, `portal.set_choice`, `portal.rights` | guest + portal session token, rate-limited, allowlisted | 2h |
| `session.create(programme, principal_ref, return_url)`, `principal.link(temp_ref, principal_ref)` | capture | 2i |

Every new guest method is added to `GUEST_ALLOWLIST` in both `ci/security_http_check.py` and `tests/test_permissions.py` in the same commit, with a comment saying what secures it.

## 6. Tests that gate each slice

- 2a: SLA overdue flips daily; access summary carries no name/phone in logs or Communication; erasure opens Purge Requests; every closure writes `rights.closed` to the feed; replies only with approved templates.
- 2b: withdrawal of purpose P reaches only processors of P and systems that `check`ed P; payload signed (HMAC-SHA256) and carries no PII; retries back off; `purge.ack` from system A can't ack system B's row; partner can't see another partner's rows.
- 2c: each start event computes the right due date; legal hold stops a purge; anonymise clears encrypted fields but leaves the chain verifying; consent records are kept for their own retention.
- 2d: minor grant without verified guardian refused; court/committee without authority ref refused; turning 18 lapses guardian consent after grace and opens a majority-transfer campaign.
- 2e–2g: inbound secret required; shared number gets "who is this for?" before any change; menus never show names; replies in `preferred_language`.
- 2h–2i: OTP brute force locked; session token scoped to one principal; toggles write signed events; return URL must match the Source System's registered host (no open redirect).
- 2j: refusal and no-response apply the fallback only after the deadline; one person never receives the same campaign twice.
- 2k: aggregates only; latest state per principal, not every event.

## 7. Decisions taken for Phase 2 (change if needed)

| Decision | Default | Why |
|---|---|---|
| First WhatsApp provider | Gupshup (BSP) adapter; Glific adapter second | Glific runs on Gupshup; many consortium NGOs already on Glific |
| IVR provider | Exotel | Common in India, DTMF + recording + call-back APIs |
| Principal login on web | No Frappe User per principal; short-lived signed portal token in Redis | Keeps beneficiaries out of Desk and the role matrix |
| Anonymise | Clear name, phone, email, DOB; keep `principal_ref` hash and flags; ledger untouched | Chain must keep verifying; events carry no PII |
| Erasure of consent evidence | Never before the consent-record retention (default 7 y) | Spec gap 11; counsel question open |
