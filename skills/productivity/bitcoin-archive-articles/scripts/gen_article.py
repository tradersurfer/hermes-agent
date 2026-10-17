#!/usr/bin/env python3
"""
BA Article Generator
====================
Takes a structured draft (dict) and emits copy-paste-ready:
  <BA_WORKFLOW or CWD>/articles/<slug>.md
  <BA_WORKFLOW or CWD>/articles/<slug>.html
following Bitcoin Archive's NEWS / TRENDING formats.

Usage:
  python gen_article.py            # runs DEMO draft
  python gen_article.py draft.json # runs a JSON draft from file
  from gen_article import build    # importable: build(draft_dict)

Draft dict schema:
{
  "category": "MARKETS",
  "type": "NEWS",            # NEWS | TRENDING
  "headline": "...",
  "date": "29 August 2026",
  "slug": "my-article-slug",
  "key_takeaway": ["Para 1.", "Para 2."],
  "body_md": "Full markdown body...  **bold** and `code` supported.",
  "asset": "C:/Users/jorda/Downloads/Bitcoin Archive/foo.png",  # optional
  "sources": ["Text – Publication (https://...)"],
  "x_posts": [ {"quote": "...", "handle": "@BitcoinArchive",
                "url": "https://x.com/.../status/<id>"}, ... ]
}
"""
import json, sys, os, re, html

ROOT = os.environ.get("BA_WORKFLOW", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ART = os.path.join(ROOT, "articles")
TEMPLATES = os.path.join(ROOT, "templates")
os.makedirs(ART, exist_ok=True)

def load(name):
    p = os.path.join(TEMPLATES, name)
    with open(p, encoding="utf-8") as f:
        return f.read()

HTML_TPL = load("article-template.html")
MD_TPL = load("article-template.md")

def md_to_html_table(block):
    rows = [r.strip().strip("|").split("|") for r in block]
    head = [c.strip() for c in rows[0]]
    data = [[c.strip() for c in r] for r in rows[2:]]
    out = ['<table style="border-collapse:collapse;width:100%;margin:18px 0;font-size:15px;">']
    out.append("<thead><tr>")
    for c in head:
        out.append(f'<th style="border:1px solid #eee;padding:8px 10px;text-align:left;background:#fafafa;">{html.escape(c)}</th>')
    out.append("</tr></thead><tbody>")
    for r in data:
        out.append("<tr>")
        for c in r:
            out.append(f'<td style="border:1px solid #eee;padding:8px 10px;">{html.escape(c)}</td>')
        out.append("</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)

def md_to_html_paras(md):
    def inline(s):
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
        return s
    out = []
    lines = md.split("\n")
    i = 0
    in_list = False
    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>"); in_list = False
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            close_list(); i += 1; continue
        if s.startswith("|") and i + 1 < len(lines) and lines[i+1].strip().startswith("|") and set(lines[i+1].strip()) <= set("|-: "):
            close_list()
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i]); i += 1
            out.append(md_to_html_table(block)); continue
        if s.startswith("### "):
            close_list(); out.append(f"<h3>{inline(html.escape(s[4:]))}</h3>"); i += 1; continue
        if s.startswith("## "):
            close_list(); out.append(f"<h2>{inline(html.escape(s[3:]))}</h2>"); i += 1; continue
        if s.startswith("> "):
            close_list()
            quote = s[2:].strip()
            out.append(f"<blockquote>{inline(html.escape(quote))}</blockquote>"); i += 1; continue
        if s.startswith("- "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{inline(html.escape(s[2:].strip()))}</li>"); i += 1; continue
        close_list()
        out.append(f"<p>{inline(html.escape(s))}</p>"); i += 1
    close_list()
    return "\n".join(out)

def build(d):
    kt = "\n".join(f"<p>{html.escape(p)}</p>" for p in d.get("key_takeaway", []))
    body_html = md_to_html_paras(d.get("body_md", ""))
    sources = "\n".join(f"<li>{html.escape(s)}</li>" for s in d.get("sources", []))
    def _md_bullet(s):
        return re.sub(r"^\s*[-*]\s+", "", s)
    asset = d.get("asset", "")
    # X posts -> real styled embeds with working status URLs
    def _quote_from(item):
        if isinstance(item, dict): return item.get("quote", "")
        return _md_bullet(item)
    def _handle_from(item):
        if isinstance(item, dict): return item.get("handle", "@BitcoinArchive")
        m = re.search(r"@([A-Za-z0-9_]+)", item)
        return "@" + m.group(1) if m else "@BitcoinArchive"
    def _url_from(item):
        if isinstance(item, dict): return item.get("url", "")
        m = re.search(r"(https?://x\.com/\S+?/status/\d+)", item)
        return m.group(1) if m else ""
    x_items = d.get("x_posts", [])
    xhtml = "\n".join(
        f'<div class="x-embed">'
        f'<a class="x-embed-link" href="{html.escape(_url_from(x) or "#")}" target="_blank" rel="noopener">'
        f'<span class="x-embed-handle">{html.escape(_handle_from(x))}</span>'
        f'<span class="x-embed-text">{html.escape(_quote_from(x))}</span>'
        f'<span class="x-embed-src">via X</span></a></div>'
        for x in x_items
    ) or '<p class="muted">None pulled for this piece.</p>'
    article = (HTML_TPL
        .replace("{{HEADLINE}}", html.escape(d["headline"]))
        .replace("{{CATEGORY}}", html.escape(d.get("category", "")))
        .replace("{{DATE}}", html.escape(d.get("date", "")))
        .replace("{{KEY_TAKEAWAY_PARAGRAPHS}}", kt)
        .replace("{{ARTICLE_BODY_HTML}}", body_html)
        .replace("{{ASSET_PATH}}", html.escape(asset))
        .replace("{{SOURCES_LIST}}", sources)
        .replace("{{X_POSTS_HTML}}", xhtml))

    def _md_x(item):
        q = _quote_from(item); h = _handle_from(item); u = _url_from(item)
        line = f"> **{h}:** {q}"
        if u: line += f"\n> _Source: {u}_"
        return line
    xposts = "\n\n".join(_md_x(x) for x in x_items) or "_None pulled for this piece._"
    sources_md = "\n".join(f"- {_md_bullet(s)}" for s in d.get("sources", [])) or "_To be added._"
    md = (MD_TPL
        .replace("{{HEADLINE}}", d["headline"])
        .replace("{{CATEGORY}}", d.get("category", ""))
        .replace("{{DATE}}", d.get("date", ""))
        .replace("{{NEWS|TRENDING}}", d.get("type", "NEWS"))
        .replace("{{SLUG}}", d.get("slug", ""))
        .replace("{{KEY_TAKEAWAY_PARAGRAPHS}}", "\n> ".join(d.get("key_takeaway", [])))
        .replace("{{ASSET_PATH}}", asset)
        .replace("{{ARTICLE_BODY_MARKDOWN}}", d.get("body_md", ""))
        .replace("{{SOURCES_LIST}}", sources_md)
        .replace("{{X_POSTS_LIST}}", xposts))

    slug = d.get("slug", "article")
    with open(os.path.join(ART, slug + ".html"), "w", encoding="utf-8") as f:
        f.write(article)
    with open(os.path.join(ART, slug + ".md"), "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[ok] {slug}.html + {slug}.md")

DEMO = {
  "category": "MARKETS", "type": "NEWS",
  "headline": "DEMO: Bitcoin's big day — El Salvador stacks, Strive buys, IBIT tops $2.3B",
  "date": "29 August 2026", "slug": "demo-article",
  "key_takeaway": ["Four signals in one session show demand is building.", "Whales keep climbing."],
  "body_md": "Intro with **bold** and `code`.\n\n### Subhead\nStrive signaled **$66M** more.\n\n> Blockquote with **bold**.\n\n- item one\n- item two with **bold**\n",
  "sources": ["Bitcoin Archive (@BitcoinArchive)"],
  "x_posts": [ {"quote":"EL SALVADOR JUST BOUGHT MORE BITCOIN.","handle":"@BitcoinArchive","url":"https://x.com/BitcoinArchive/status/2093497856342512037"} ],
}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            build(json.load(f))
    else:
        build(DEMO)
