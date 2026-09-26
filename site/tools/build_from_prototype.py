#!/usr/bin/env python3
"""Regenerate the public website from docs/anumati-prototype.html.

The website is lifted, not redrawn (CLAUDE.md): CSS tokens, mark(), wordmark(), maina(), icon64(),
heroArt() and the six website pages are copied verbatim from the prototype. Only the glue changes:
hash routing instead of the prototype's "View as" bar, links into the hosted prototype for the
product surfaces, and a mailto sandbox form instead of a fake submit.

Run from the repo root after the prototype changes:  python3 site/tools/build_from_prototype.py
"""

import pathlib
import re
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "docs" / "anumati-prototype.html"
OUT = ROOT / "site"

html = SRC.read_text(encoding="utf-8")
lines = html.split("\n")


def line_of(prefix: str) -> int:
	for i, line in enumerate(lines):
		if line.startswith(prefix):
			return i
	raise SystemExit(f"marker not found in prototype: {prefix!r}")


css = html[html.index("<style>") + len("<style>") : html.index("</style>")].strip("\n")
helpers = "\n".join(lines[line_of("const esc") : line_of("const PURPOSES")])
art_and_site = "\n".join(lines[line_of("/* ================= ART") : line_of("/* ================= NGO CONSOLE")])

REPLACE = [
	# Sandbox form: no fake sample values, and say honestly what happens on submit.
	(' required value="Aaroh Foundation"', ' required placeholder="Your organisation" autocomplete="organization"'),
	(' required value="Priya M."', ' required placeholder="Your name" autocomplete="name"'),
	('<input id="d-n" value="25,000">', '<input id="d-n" placeholder="e.g. 25,000" inputmode="numeric">'),
	("Prototype: nothing is sent.", "Opens your email app with these details. This website stores nothing."),
	("Write to us. I’ll carry it over. (Nothing is sent from this prototype.)", "Write to us. I’ll carry it over."),
	# On 1260–1450 px screens the curved thread overshoots the viewport; keep Maina on screen.
	("translate(${(pt.x - 34).toFixed(1)}px", "translate(${(Math.min(Math.max(pt.x, 40), W - 40) - 34).toFixed(1)}px"),
]
for old, new in REPLACE:
	if old not in art_and_site:
		raise SystemExit(f"expected text not found in prototype: {old!r}")
	art_and_site = art_and_site.replace(old, new)

RUNTIME = r"""
/* ================= Site runtime (the only part not lifted from the prototype) ================= */
const SITE = {
  contactEmail: '',        // set to the team inbox to make "Request a sandbox" open an email
  consoleUrl: '',          // set to the Frappe Cloud site URL once it is live ("Sign in")
  prototypeUrl: 'prototype/'
};
const S = { site: { page: 'home' } };
const PAGE_TITLES = Object.fromEntries(SITE_PAGES);
function pageFromHash(){ const h = location.hash.slice(1); return PAGE_TITLES[h] ? h : 'home'; }
function toast(msg){
  const el = document.getElementById('toast');
  el.className = 'toast'; el.textContent = msg; el.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => { el.hidden = true; }, 6000);
}
function render(){
  S.site.page = pageFromHash();
  document.getElementById('app').innerHTML = renderSite();
  document.title = S.site.page === 'home' ? 'Anumati · Consent that works where the internet doesn’t' : `${PAGE_TITLES[S.site.page]} · Anumati`;
  setupIO(); storyInit();
}
const lensUrl = k => (k === 'con' && SITE.consoleUrl) ? SITE.consoleUrl : `${SITE.prototypeUrl}#${k}`;
document.addEventListener('click', e => {
  const el = e.target.closest('[data-a]'); if (!el) return;
  if (el.dataset.a === 'site'){
    e.preventDefault();
    if (pageFromHash() === el.dataset.p) render(); else location.hash = el.dataset.p;
    window.scrollTo(0, 0);
  } else if (el.dataset.a === 'lens'){
    e.preventDefault(); location.href = lensUrl(el.dataset.k);
  }
});
window.addEventListener('hashchange', () => { render(); window.scrollTo(0, 0); });
document.addEventListener('submit', e => {
  if (e.target.dataset.form !== 'demo') return;
  e.preventDefault();
  const v = id => document.getElementById(id).value.trim();
  if (!SITE.contactEmail){ toast('Sandbox requests open soon. Thank you for your interest.'); return; }
  const body = `Organisation: ${v('d-org')}\nName: ${v('d-name')}\nHow we collect data today: ${v('d-sys')}\nPeople served per year: ${v('d-n')}\n`;
  location.href = `mailto:${SITE.contactEmail}?subject=${encodeURIComponent('Anumati sandbox request: ' + v('d-org'))}&body=${encodeURIComponent(body)}`;
});
render();
"""

js = (
	"/* Anumati website. Lifted from docs/anumati-prototype.html by site/tools/build_from_prototype.py.\n"
	"   Edit the prototype, then regenerate; hand edits here are overwritten. */\n"
	+ helpers + "\n\n" + art_and_site + "\n" + RUNTIME
)

(OUT / "assets").mkdir(parents=True, exist_ok=True)
(OUT / "assets" / "site.css").write_text(
	"/* Lifted verbatim from docs/anumati-prototype.html (CSS tokens, components, website, motion). */\n" + css + "\n",
	encoding="utf-8",
)
(OUT / "assets" / "site.js").write_text(js, encoding="utf-8")

# The full clickable prototype, with a deep link (#app, #ben, #con ...) to open a surface directly.
deeplink = (
	"(function(){ const h = location.hash.slice(1); if (h && LENSES.some(x => x[0] === h)){ S.lens = h;"
	" try { localStorage.setItem('anumati-lens', h); } catch(e) {} } })();\n"
)
init = "(function init(){"
if init not in html:
	raise SystemExit("prototype init() not found")
proto = html.replace(init, deeplink + init, 1)
(OUT / "prototype").mkdir(exist_ok=True)
(OUT / "prototype" / "index.html").write_text(proto, encoding="utf-8")

# Favicon rendered from the prototype's own mark() (needs Node; skipped if unavailable).
mark_src = "\n".join(lines[line_of("let _mk") : line_of("function wordmark")])
if shutil.which("node"):
	svg = subprocess.run(
		["node", "-e", mark_src + "\nprocess.stdout.write(mark(64).replace(' class=\"logo\"', ' xmlns=\"http://www.w3.org/2000/svg\"'))"],
		check=True, capture_output=True, text=True,
	).stdout
	(OUT / "assets" / "favicon.svg").write_text(re.sub(r"\s+\n", "\n", svg), encoding="utf-8")

print("site rebuilt:", ", ".join(str(p.relative_to(ROOT)) for p in sorted(OUT.rglob("*")) if p.is_file() and "tools" not in p.parts))
