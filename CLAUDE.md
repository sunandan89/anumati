# Anumati — working notes for Claude Code

Anumati is an open-source, field-first DPDP consent platform for nonprofits, built as a Frappe app (`anumati`, AGPL-3.0).

## Source of truth

- `docs/anumati-spec-v0.4.md` (current; v0.3 kept for history) — behaviour, data model, rules, security, APIs. Wins on data, rules and security.
- `docs/anumati-prototype.html` — look, copy, flows across eight surfaces. Wins on UX and copy. Lift CSS tokens, `mark()`, `maina()`, `icon64()`, `heroArt()` from it; do not redraw.

## Non-negotiables

- Tests before features. CI must block merges on: unauthenticated routes return 401/403; cross-tenant isolation; Consent Event and Audit Entry are insert-only (saving an existing one raises); hash-chain tamper detection.
- Config before code: DocType JSON and fixtures first; Python only for signing, chain, sync, channels, enforcement.
- No PII in logs. Field-level encryption for name, phone, evidence. Phone lookups by salted hash.
- All sample data is fictional.

## Layout (planned)

- `anumati/` — Frappe app (server, console, portals, APIs)
- `site/` — static public website, deployed to GitHub Pages
- `.github/workflows/` — CI (MariaDB + Redis services, Frappe bench, tests)

Other repos later: `anumati_collect` (Flutter on `frappe_mobile_sdk`), `anumati_connectors`, `anumati_client`, `anumati_platform`.

## Hosting

- Server: Frappe Cloud, Mumbai region, deployed from this GitHub repo.
- Website: GitHub Pages.

## Current phase

Phase 0 — Foundations (spec section 11).
