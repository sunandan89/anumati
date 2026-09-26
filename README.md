# Anumati

Consent that works where the internet doesn't — an open-source DPDP consent platform for nonprofits, built on Frappe.

- Offline and assisted consent capture, guardian flows, multi-channel withdrawal
- Append-only, signed, hash-chained consent ledger
- Hosted (India region) or self-hosted

Status: pre-alpha, Phase 0 (foundations). See [`docs/anumati-spec-v0.4.md`](docs/anumati-spec-v0.4.md).

## What's here

| Path | What |
|---|---|
| `anumati/` | Frappe v15 app: DocTypes (JSON), fixtures (roles, workflows, custom fields), signing and hash chain, tests |
| `site/` | Public website (static, GitHub Pages), lifted from the prototype; `site/prototype/` is the clickable prototype |
| `ci/` | HTTP security gate (unauthenticated routes, tenant isolation) and a Frappe-free ledger self-test |
| `docs/phase-0-foundations.md` | How the spec maps onto stock Frappe, ledger design, role matrix, CI gates |
| `docs/setup-guide.md` | Click-by-click: branch protection, GitHub Pages, Frappe Cloud |

Licence: AGPL-3.0 (server).
