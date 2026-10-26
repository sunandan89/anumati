#!/usr/bin/env python3
"""CI gate over real HTTP against a running bench with two tenant sites.

1. Unauthenticated requests to every Anumati DocType route and every non-guest method get 401/403.
2. Guest methods are exactly the reviewed allowlist.
3. Tenant isolation: tenant A's API key cannot read tenant B's records (and vice versa), and one
   tenant's consent hash does not verify on the other.

Usage: security_http_check.py BASE_URL SITE_A SITE_B A.json B.json inventory.json
"""

import json
import sys
from urllib.parse import quote

import requests

GUEST_ALLOWLIST = {
	"anumati.api.v1.consent.verify",
	"anumati.api.v1.consent.public_keys",
	# SMS gateway callbacks: POST only, with the Channel Provider inbound secret in the X-Anumati-Token header
	"anumati.api.v1.channel.inbound_sms",
	"anumati.api.v1.channel.missed_call",
	"anumati.api.v1.channel.delivery_report",
	# Self-service page (/my-consent). Signing in: an SMS code to a number we hold, or a receipt code and year
	# of birth; rate-limited, with tries counted per number and per code.
	"anumati.selfservice.start",
	"anumati.selfservice.verify",
	"anumati.selfservice.code_login",
	"anumati.selfservice.home",
	"anumati.selfservice.sign_out",
	"anumati.selfservice.choose",
	# Signed in only: each one needs the page's session cookie and answers 401 without it.
	"anumati.selfservice.overview",
	"anumati.selfservice.save_choices",
	"anumati.selfservice.leave",
	"anumati.selfservice.receipt",
	"anumati.selfservice.ask",
	"anumati.selfservice.write",
	"anumati.selfservice.complain",
	"anumati.selfservice.respond",
}
DENIED = {401, 403}

base, site_a, site_b, file_a, file_b, file_inv = sys.argv[1:7]
creds = {site_a: json.load(open(file_a)), site_b: json.load(open(file_b))}
inv = json.load(open(file_inv))
failures, checks = [], 0


def call(method, site, path, token=None, **kw):
	headers = {"Host": site, "Accept": "application/json"}
	if token:
		headers["Authorization"] = f"token {token['api_key']}:{token['api_secret']}"
	return requests.request(method, base + path, headers=headers, timeout=30, allow_redirects=False, **kw)


def expect(ok, label):
	global checks
	checks += 1
	if not ok:
		failures.append(label)


# 1. unauthenticated sweep
for site in (site_a, site_b):
	for dt in inv["doctypes"]:
		q = quote(dt)
		for method, path in (("GET", f"/api/resource/{q}"), ("POST", f"/api/resource/{q}"),
		                     ("GET", f"/api/v2/document/{q}")):
			r = call(method, site, path)
			expect(r.status_code in DENIED, f"{site} {method} {path} -> {r.status_code}")
	for m in inv["methods"]:
		if m in GUEST_ALLOWLIST:
			continue
		for method, path in (("GET", f"/api/method/{m}"), ("POST", f"/api/method/{m}"), ("POST", f"/api/v2/method/{m}")):
			r = call(method, site, path)
			expect(r.status_code in DENIED, f"{site} unauthenticated {method} {path} -> {r.status_code}")

	r = call("GET", site, f"/api/resource/{quote('Anumati Consent Event')}/{creds[site]['event']}")
	expect(r.status_code in DENIED, f"{site} unauthenticated read of a real consent event -> {r.status_code}")

	for cb in ("inbound_sms", "missed_call", "delivery_report"):
		r = call("POST", site, f"/api/method/anumati.api.v1.channel.{cb}", data={"provider": "x", "token": "wrong", "sender": "9000000000"})
		expect(r.status_code in DENIED, f"{site} {cb} with a wrong secret -> {r.status_code}")
		r = call("GET", site, f"/api/method/anumati.api.v1.channel.{cb}?provider=x&sender=9000000000")
		expect(r.status_code in DENIED | {405}, f"{site} {cb} by GET -> {r.status_code}")

	# The self-service page's signed-in methods refuse anyone without its session cookie.
	for m in ("overview", "save_choices", "leave", "ask", "write", "choose", "complain", "respond"):
		r = call("POST", site, f"/api/method/anumati.selfservice.{m}", data={"i": 0, "programme": "x", "request_type": "access",
		                                                                         "request": "x", "text": "x", "year": 1990,
		                                                                         "category": "something_else", "details": "x",
		                                                                         "grievance_name": "x", "solved": 1})
		expect(r.status_code == 401, f"{site} self-service {m} without a session -> {r.status_code}")
	r = call("GET", site, "/api/method/anumati.selfservice.receipt?i=0&event=x")
	expect(r.status_code == 401, f"{site} self-service receipt without a session -> {r.status_code}")
	r = call("GET", site, "/my-consent")
	expect(r.status_code == 200, f"{site} /my-consent page -> {r.status_code}")

# 2. guest allowlist
expect(set(inv["guest"]) == GUEST_ALLOWLIST, f"guest methods changed: {sorted(set(inv['guest']) ^ GUEST_ALLOWLIST)}")

# 3. tenant isolation
ev = quote("Anumati Consent Event")
for own, other in ((site_a, site_b), (site_b, site_a)):
	me, them = creds[own], creds[other]
	r = call("GET", own, f"/api/resource/{ev}/{me['event']}", token=me)
	expect(r.status_code == 200, f"positive control: {own} key reading own event -> {r.status_code}")
	r = call("GET", other, f"/api/resource/{ev}/{them['event']}", token=me)
	expect(r.status_code in DENIED, f"{own} key reading {other} event -> {r.status_code}")
	r = call("GET", other, f"/api/resource/{ev}", token=me)
	expect(r.status_code in DENIED, f"{own} key listing {other} events -> {r.status_code}")
	r = call("GET", other, "/api/method/anumati.api.v1.chain.verify", token=me)
	expect(r.status_code in DENIED, f"{own} key verifying {other} chain -> {r.status_code}")
	chk = {"principal_ref": "CI-NOBODY", "purpose": "CI-screen"}
	r = call("GET", own, "/api/method/anumati.api.v1.consent.check", token=me, params=chk)
	expect(r.status_code == 200, f"positive control: {own} key calling own consent.check -> {r.status_code}")
	r = call("GET", other, "/api/method/anumati.api.v1.consent.check", token=me, params=chk)
	expect(r.status_code in DENIED, f"{own} key calling {other} consent.check -> {r.status_code}")
	r = call("GET", other, "/api/method/anumati.api.v1.consent.verify", params={"hash": me["hash"]})
	expect(r.status_code == 200 and r.json()["message"]["in_chain"] is False,
	       f"{own} consent hash must not be on {other}'s chain -> {r.status_code} {r.text[:200]}")
	r = call("GET", own, "/api/method/anumati.api.v1.consent.verify", params={"hash": me["hash"]})
	expect(r.status_code == 200 and r.json()["message"]["signature_valid"] is True,
	       f"{own} consent hash should verify on its own chain -> {r.status_code}")

print(f"{checks} checks, {len(failures)} failed")
for f in failures:
	print("FAIL:", f)
sys.exit(1 if failures else 0)
