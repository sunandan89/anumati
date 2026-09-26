# Phase 0 — Foundations: how Anumati sits on Frappe

Spec: `docs/anumati-spec-v0.4.md` §11 (Phase 0). Principle agreed for this build: **use what Frappe already does, configure it, and write code only where Frappe has nothing.** Anumati is one standard Frappe v15 app (`anumati`) with one module (`Anumati`). It never patches or overrides Frappe.

## 1. Capability map — spec need → stock Frappe feature

| Spec need | Frappe feature used | Code? |
|---|---|---|
| Login, sessions, password policy | Frappe auth, System Settings | No |
| 2FA for anyone with PII access (v0.4) | Role → *Two Factor Authentication*, System Settings → *Enable 2FA* (switched on at install) | No |
| Staff SSO (Google, Microsoft, SAML/OIDC) | Social Login Key | No |
| API keys, mobile app login, key scopes | User API key/secret, OAuth Client; scope = roles on the API user | No |
| Role matrix (§2) | DocType permissions, Role (fixtures), Role Profile, User Permission (limit a user to a programme) | No |
| Encrypt name, phone, witness, nominee, provider credentials | Password fieldtype (encrypted with the site key) | No |
| Who viewed which principal (PII Access Log) | *Track Views* → stock **View Log**; exports → stock **Access Log** | No |
| Change history of every record | *Track Changes* → stock **Version**; deletions → **Deleted Document** | No |
| Notice publish gate + DPIA sign-off (v0.4, T18) | Two stock **Workflows** (fixtures): *Notice Publishing*, *ROPA Approval* | No (conditions are Workflow expressions) |
| Notice versions, published = immutable | Submittable DocType + Amend | No |
| Inbox thread across channels (T4), channel messages | Stock **Communication** + timeline, 5 Custom Fields (fixtures) | No |
| Language pack | Stock **Translation** + 4 Custom Fields (fixtures) | No |
| Jobs and exports log | Stock **Data Import**, **Prepared Report**, **RQ Job**, **Scheduled Job Log** | No |
| Receipts, confirmations, reminders (later) | Notification, Email Template, SMS Settings, Jinja | No |
| Printed receipt / slip, audit pack PDF (later) | Print Format | No |
| Webhooks with HMAC + delivery log (later) | Webhook (has a signing secret), Webhook Request Log | No |
| Assign requests, SLA reminders (later) | Assign To, Assignment Rule, Notification (days before/after) | No |
| Dashboards, analytics (later) | Workspace, Number Card, Dashboard Chart, Query Report | No |
| Portals, auditor share links (later) | Portal pages, Web Form, Document Share Key | No |
| Nightly jobs | `scheduler_events` in `hooks.py` | Config |
| One tenant per site | Bench multi-site | No |
| **Ed25519 signing, hash chain, verifier** | — nothing in Frappe | **Yes** `anumati/ledger/` |
| **Insert-only Consent Event / Audit Entry** | Permissions (no write/delete for anyone) + standard `validate` / `on_trash` hooks | **Small** |
| **Phone lookup by salted hash** | — | **Small** `anumati/pii.py` |
| Consent check < 50 ms, channel receivers (Phase 1–2) | — | Later, per spec |

Only three documented controller hooks are used (`validate`, `before_save`, `on_trash`). No Frappe method is overridden.

## 2. Data model

Spec §7 lists 32 DocTypes. 28 are built as Anumati DocTypes (JSON in `anumati/anumati/doctype/`); 4 are stock Frappe:

| Spec DocType | Built as |
|---|---|
| PII Access Log | stock View Log (track_views on Data Principal, Guardian Link, Consent Event, Rights Request) + Access Log |
| Job & Export Log | stock Data Import / Prepared Report / RQ Job / Scheduled Job Log |
| Channel Message | stock Communication + Custom Fields `anumati_channel`, `anumati_sender_hash`, `anumati_provider`, `anumati_message_template`, `anumati_consent_event`. Phone numbers are **not** written to `phone_no`; only the salted hash |
| Language Pack Entry | stock Translation + Custom Fields `anumati_audio`, `anumati_reviewer`, `anumati_reviewed_on`, `anumati_pack_version` |

Anumati DocTypes: Anumati Settings, Programme, Purpose, Notice Template, Notice Translation, Data Principal (+ Nominee), Guardian Link, Consent Event, Consent State, Verification Attempt, Rights Request, Channel Provider, Processor, Propagation Ack, Campaign, Purge Request, ROPA Entry, Breach Incident, Audit Entry, Source System, System Usage Log, Message Template, Field Device, Audit Share, Funder Link, Retention Policy, Data Category — plus small child tables (languages, capture modes, verification methods, withdrawal channels, notice purposes/processors, etc.).

v0.4 changes carried into the model: Retention Policy (duration, clock start = collection / withdrawal / relationship ended, action at expiry, systems told); Data Category; notice processors, cross-border line and per-language button labels; DPIA fields and DPO approval on ROPA; breach types, programme, 72-hour step timestamps; "relationship ended" on principals; "lost" device status; evidence hash and deletion reference on partner acknowledgements (T15).

Tenant platform DocTypes (Tenant, Usage Record) belong to `anumati_platform`, not this repo.

## 3. Ledger design

- **Two chains per tenant** (one site = one tenant): Consent Event and Audit Entry.
- `hash = sha256(canonical_json(payload) + prev_hash)`; genesis `prev_hash` is 64 zeros. Canonical JSON: sorted keys, no spaces, UTF-8. The payload is a fixed field list per chain (`anumati/ledger/chain.py`), each field normalised to a type so a row read back from MariaDB hashes identically.
- The tenant **Ed25519** key signs the hash. `key_id` (first 16 hex of sha256(public key)) is inside the signed payload. Rotation keeps old public keys in Anumati Settings → *Retired public keys*, so old events keep verifying (spec §9).
- Key storage: generated on install into Anumati Settings (Password field, encrypted with the site key). A site-config value `anumati_signing_key` overrides it for ops-managed or KMS keys. Nobody ever handles the key by hand.
- Encrypted values (witness) are chained as a SHA-256 digest, never in clear. Values containing `<`/`>` are refused, because Frappe sanitises markup after `before_save`.
- **Concurrency:** the head row is read with Frappe's `get_value(..., for_update=True)`; unique indexes on `chain_seq` and `hash` make a fork impossible.
- **Consent Event is never edited.** Later confirmation lives in Verification Attempt and Consent State; withdrawal is a new event (D4).
- **Admin audit:** Frappe already writes Version and Deleted Document records. Every 10 minutes, `seal_audit_trail` seals new ones for Anumati DocTypes and access-control DocTypes (User, Role, Role Profile, User Permission, Custom DocPerm, DocShare, Workflow, Webhook, Notification, Social Login Key, System Settings) into the Audit Entry chain as hashes plus changed field names — never values.
- **Verification:** `verify_chain` checks sequence, links, hashes and signatures; the nightly job also checks against yesterday's checkpoint, so truncation is caught. Failures go to Error Log (no PII). DPOs can run it any time: `/api/v2/method/anumati.api.v1.chain.verify`.
- **Public verify:** `/api/v2/method/anumati.api.v1.consent.verify?hash=…` (guest, rate-limited) and `…consent.public_keys` let anyone verify an artefact or an export without seeing personal data.

## 4. CI gates (block merges once branch protection is on)

| Gate | Where |
|---|---|
| Unauthenticated requests to every Anumati DocType route and every non-guest method return 401/403 | `ci/security_http_check.py` over real HTTP, plus `tests/test_permissions.py` |
| Guest-callable methods are exactly the reviewed allowlist | both of the above |
| Cross-tenant isolation: tenant A's key can't read tenant B (and vice versa); A's hashes don't verify on B | `ci/security_http_check.py` with two sites |
| Consent Event and Audit Entry: saving or deleting an existing one raises; no role has write/delete | `tests/test_insert_only.py` |
| Hash chain detects edited fields, re-hashed rows, forged signatures, deleted rows, truncation; rotation keeps old signatures valid; admin changes are sealed | `tests/test_chain.py` |
| Role matrix matches the reviewed `tests/role_matrix.json`; 2FA on PII roles | `tests/test_permissions.py` |
| Name/phone/witness not stored in clear; phone hash salted and normalised | `tests/test_pii.py` |
| Notice can't publish without Rule 3 contents and approved ROPA; DPIA blocks ROPA approval until complete | `tests/test_workflow.py` |

## 5. Role matrix (spec §2)

Roles ship as Role fixtures: Anumati Admin, DPO, Operator, Programme Manager, Field Worker, Developer, Auditor, Processor Partner, Funder Viewer. 2FA is on for Admin, DPO, Operator and Programme Manager (anyone with PII access in Desk). Field Worker, Auditor, Partner and Funder have no Desk access. The Platform Operator role belongs to `anumati_platform`.

| DocType | Admin | DPO | Operator | Prog. Mgr | Field Worker | Developer | Auditor | Partner | Funder | System Mgr |
|---|---|---|---|---|---|---|---|---|---|---|
| Anumati Settings | Edit | View |  |  |  |  |  |  |  | Edit |
| Audit Entry | Read | Read + export |  |  |  |  | View |  |  | Read |
| Audit Share | Read | Full |  |  |  |  |  |  |  | Full |
| Breach Incident | Full | Full |  |  |  |  |  |  |  | Full |
| Campaign | Full | Create/edit | Read | Create/edit |  |  |  |  |  | Full |
| Channel Provider | Full |  |  |  |  |  |  |  |  | Full |
| Consent Event | Read + export | Read + export | Read | Read | Create only |  |  |  |  | Create only |
| Consent State | Read | Read | Read | Read | View | View |  |  |  | Full |
| Data Category | Full | Create/edit | View | Create/edit | View |  |  |  |  | Full |
| Data Principal | Full | Create/edit | Create/edit | Read | Create/edit |  |  |  |  | Full |
| Field Device | Full |  |  | Create/edit | View |  |  |  |  | Full |
| Funder Link | Full | Create/edit |  |  |  |  |  |  | View | Full |
| Guardian Link | Full | Create/edit | Create/edit | Read | Create/edit |  |  |  |  | Full |
| Message Template | Full | Create/edit | Read | Create/edit |  |  |  |  |  | Full |
| Notice Template | Read | Full + publish | Read | Read | View | View |  |  |  | Full + publish |
| Notice Translation | Full | Create/edit | Read | Create/edit | View |  |  |  |  | Full |
| Processor | Full | Create/edit | Read |  |  |  |  | View |  | Full |
| Programme | Full | Read | Read | Create/edit | View | View |  |  |  | Full |
| Propagation Ack | Read | Create/edit | Create/edit |  |  |  |  | View |  | Full |
| Purge Request | Full | Create/edit | Create/edit |  |  |  |  |  |  | Full |
| Purpose | Full | Create/edit | Read | Create/edit | View | View |  |  |  | Full |
| ROPA Entry | Read | Full |  | Read |  |  | View |  |  | Full |
| Retention Policy | Full | Create/edit |  | Read |  |  |  |  |  | Full |
| Rights Request | Full | Full | Create/edit | Read | Create only |  |  |  |  | Full |
| Source System | Full | Read |  |  |  | Create/edit |  |  |  | Full |
| System Usage Log | Read | Read |  |  |  | View |  |  |  | Read |
| Verification Attempt | Read | Read | Create/edit | Read | Create only |  |  |  |  | Full |

"Full + publish" = can submit/cancel/amend (notices). Notice publishing and ROPA approval are further limited by their Workflows to the DPO. Row-level limits (e.g. a field worker sees only their programme) use stock User Permissions, set per user.
