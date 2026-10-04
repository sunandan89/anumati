"""Builds the product guide and the QA test cases (docs/guide/*.md) into site/guide/ for GitHub Pages.

The Markdown in docs/guide/ is the source: GitHub shows it (Mermaid flowcharts included), and the Pages
workflow runs this on every merge to main, so the published guide always matches the merged code.
Run from the repo root: python3 tools/build_guide.py (needs `pip install markdown`)."""

import html
import os
import re
import shutil

import markdown

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "docs", "guide")
OUT = os.path.join(REPO, "site", "guide")
PAGES = (("product-guide.md", "index.html"), ("qa-test-cases.md", "qa-test-cases.html"))
SOURCE_URL = "https://github.com/sunandan89/anumati/blob/main/docs/guide/"

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ --ground:#F3EADB; --surface:#FFFDF8; --ink:#2A2118; --ink2:#5C4F40; --line:#E9DCC6; --terra:#B4532A; --leaf:#3E6B3A; }}
@media (prefers-color-scheme: dark) {{ :root {{ --ground:#1E1A15; --surface:#28231C; --ink:#F3EADB; --ink2:#CDBFAA; --line:#3D352B; --terra:#E08A5C; --leaf:#8DBA86; }} }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--ground); color:var(--ink); font:16px/1.6 "Noto Sans", system-ui, sans-serif; }}
nav {{ background:var(--leaf); color:#F4F8EF; padding:12px 16px; display:flex; gap:16px; flex-wrap:wrap; font-size:14px; }}
nav a {{ color:#F4F8EF; }}
main {{ max-width:960px; margin:0 auto; padding:16px; }}
h1 {{ font-size:28px; line-height:1.25; }} h2 {{ margin-top:40px; border-bottom:1px solid var(--line); padding-bottom:4px; }}
a {{ color:var(--terra); }}
.table {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; background:var(--surface); font-size:14px; }}
th, td {{ border:1px solid var(--line); padding:6px 8px; text-align:left; vertical-align:top; }}
th {{ background:var(--line); }}
code {{ background:var(--line); padding:1px 4px; border-radius:4px; }}
blockquote {{ margin:16px 0; padding:8px 16px; border-left:4px solid var(--terra); background:var(--surface); }}
pre.mermaid {{ background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:12px; text-align:center; overflow-x:auto; }}
footer {{ color:var(--ink2); font-size:13px; padding:24px 16px; text-align:center; }}
</style>
</head>
<body>
<nav><strong>Anumati</strong><a href="index.html">Product guide</a><a href="qa-test-cases.html">QA test cases</a><a href="{source}">Source on GitHub</a></nav>
<main>
{body}
</main>
<footer>Built from <a href="{source}">docs/guide/{name}</a> on every merge to main.</footer>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{ startOnLoad: true, theme: window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "neutral" }});</script>
</body>
</html>
"""


def render(text: str) -> str:
    # Mermaid blocks become <pre class="mermaid"> for the browser to draw; everything else is Markdown.
    blocks = []

    def keep(m):
        blocks.append(f'<pre class="mermaid">{html.escape(m.group(1))}</pre>')
        return f"\n\nMERMAIDBLOCK{len(blocks) - 1}\n\n"

    text = re.sub(r"```mermaid\n(.*?)```", keep, text, flags=re.S)
    body = markdown.markdown(text, extensions=["tables", "toc", "fenced_code", "sane_lists"])
    body = re.sub(r"<p>MERMAIDBLOCK(\d+)</p>", lambda m: blocks[int(m.group(1))], body)
    body = body.replace("<table>", '<div class="table"><table>').replace("</table>", "</table></div>")
    return body.replace('href="qa-test-cases.md"', 'href="qa-test-cases.html"').replace(
        'href="product-guide.md"', 'href="index.html"')


def main():
    os.makedirs(OUT, exist_ok=True)
    # Wireframe images the guide shows, next to the pages.
    shutil.copytree(os.path.join(SRC, "wireframes"), os.path.join(OUT, "wireframes"), dirs_exist_ok=True)
    for name, out in PAGES:
        with open(os.path.join(SRC, name), encoding="utf-8") as fh:
            text = fh.read()
        title = re.search(r"^# (.+)$", text, re.M).group(1)
        page = PAGE.format(title=html.escape(title), body=render(text), source=SOURCE_URL + name, name=name)
        with open(os.path.join(OUT, out), "w", encoding="utf-8") as fh:
            fh.write(page)
        print("wrote", os.path.relpath(os.path.join(OUT, out), REPO))


if __name__ == "__main__":
    main()
