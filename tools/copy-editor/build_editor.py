#!/usr/bin/env python3
"""Build a WYSIWYG copy editor artifact from the real site files.

Renders each page exactly as it appears, with every copy block made
editable in place. Edits persist to the artifact db keyed by block id,
so they can be read back and merged into the HTML.
"""
import base64
import io
import json
import os
import re
from pathlib import Path

from bs4 import BeautifulSoup, Comment
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]

PAGES = [
    ("index",    "index.html",    "Home"),
    ("events",   "events.html",   "Events"),
    ("about",    "about.html",    "About"),
    ("faq",      "faq.html",      "Policies & FAQ"),
    ("contact",  "contact.html",  "Contact"),
    ("404",      "404.html",      "404 page"),
]

PAGE_KEYS = {k for k, _, _ in PAGES}

TAGGABLE = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "span",
            "td", "summary", "figcaption", "small", "div", "a", "button"}


def norm(s):
    s = re.sub(r"\s+", " ", s or "").strip()
    return re.sub(r"\s+([,.;:!?%])", r"\1", s)


# ---------------------------------------------------------------- images
def image_data_uri(path, max_w=900, quality=72):
    """Downscale an asset and return a data: URI. Keeps the artifact small."""
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (244, 241, 234))  # --paper
        bg.paste(im, mask=im.split()[-1] if im.mode == "RGBA" else None)
        im = bg
    else:
        im = im.convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


print("→ encoding images")
IMAGES = {}
for f in sorted(os.listdir(ROOT / "assets")):
    p = ROOT / "assets" / f
    try:
        IMAGES[f] = image_data_uri(p)
        print(f"   {f}: {len(IMAGES[f])//1024} KB")
    except Exception as e:
        print(f"   !! {f}: {e}")


# ------------------------------------------------------------- copy deck
def parse_deck():
    """Read copy-deck.md -> {block_id: {text, note, src, line, mine}}.

    `mine` marks a block already in Marci's own words (a YOURS line)."""
    deck = {}
    txt = (ROOT / "copy-deck.md").read_text(encoding="utf-8")
    for chunk in re.split(r"^### ", txt, flags=re.M)[1:]:
        lines = chunk.split("\n")
        bid = lines[0].strip()
        src, note, mine, body = "", "", False, []
        for ln in lines[1:]:
            if ln.startswith("---") or ln.startswith("#"):
                break
            if ln.startswith("`") and not src:
                src = ln.strip("` ")
            elif ln.startswith("NOTE:"):
                note = ln[5:].strip()
            elif ln.strip() == "YOURS":
                mine = True
            elif ln.strip():
                body.append(ln.strip())
        if bid and body:
            m = re.search(r":(\d+)", src)
            deck[bid] = {"text": " ".join(body), "note": note, "src": src,
                         "line": int(m.group(1)) if m else 0, "mine": mine}
    return deck


DECK = parse_deck()
print(f"→ parsed {len(DECK)} deck blocks")


# ------------------------------------------------------------ page build
def build_page(html_path, page_key):
    """Return (srcdoc_html, meta, tagged_count, mine_ids, missed_ids).

    page_key must match the key used in PAGES."""
    soup = BeautifulSoup((ROOT / html_path).read_text(encoding="utf-8"), "html.parser")

    meta = {"title": "", "description": ""}
    if soup.title:
        meta["title"] = norm(soup.title.get_text())
    md = soup.find("meta", attrs={"name": "description"})
    if md:
        meta["description"] = md.get("content", "")

    # scripts and json-ld carry no visible copy
    for t in soup.find_all(["script", "noscript"]):
        t.decompose()

    # developer comments are not content and must not render
    for c in soup.find_all(string=lambda x: isinstance(x, Comment)):
        c.extract()

    # assets -> data URIs
    for img in soup.find_all("img"):
        src = (img.get("src") or "").split("/")[-1]
        if src in IMAGES:
            img["src"] = IMAGES[src]
        else:
            img.decompose()

    # resolve in-site links to page keys so the real nav drives the editor
    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()
        target, frag = (href.split("#", 1) + [""])[:2]
        target = target.replace("../", "").lstrip("./")
        if target.endswith(".html"):
            key = target.replace(".html", "")
        elif not target and frag:
            key = page_key          # pure in-page anchor
        else:
            key = None
        if key and key in PAGE_KEYS:
            a["data-goto"] = key
            if frag:
                a["data-goto-hash"] = frag
        elif href and not href.startswith("javascript:"):
            a["data-external"] = href
        a["href"] = "javascript:void(0)"

    # every FAQ answer visible at rest
    for d in soup.find_all("details"):
        d["open"] = ""

    # ---- tag editable blocks by matching deck text
    want = {bid: v for bid, v in DECK.items() if v["src"].split(":")[0] == html_path}

    # meta blocks live in the chrome, not the page body
    body_want = {b: v for b, v in want.items()
                 if not re.search(r"meta-(title|description)|og-description", b)}

    # Navigation chrome is not deck content. Without this, a nav link whose
    # label matches a block's text (e.g. "Areas Served") gets claimed as that
    # block: the link stops navigating, and a merge would write body copy into
    # the site's menu.
    def in_chrome(el):
        for a in el.parents:
            cls = a.get("class") or []
            if a.name in ("header", "nav"):
                return True
            if {"breadcrumbs", "nav-links", "nav-cta", "mobile-book"} & set(cls):
                return True
            if a.name == "ul" and a.find_parent("footer"):
                return True
        return False

    # <br> and inline <em> must read as word breaks, so join with a space
    candidates = [e for e in soup.find_all(TAGGABLE)
                  if e.get_text(strip=True) and not in_chrome(e)]
    index = {}
    for e in candidates:
        index.setdefault(norm(e.get_text(" ")), []).append(e)

    tagged, missed, mine = 0, [], []
    used = set()

    def claim(bid, text, v, note):
        nonlocal tagged
        matches = [e for e in index.get(norm(text), []) if id(e) not in used]
        if not matches:
            return False
        # A wrapper whose child carries the same text is not the owner; the
        # innermost element is.
        ids = {id(e) for e in matches}
        inner = [e for e in matches if not any(id(d) in ids for d in e.find_all(True))]
        # The same words can appear twice on one page (the home hero and the
        # footer tagline are both "Clinical Care, Anywhere."), so the deck's
        # line number decides which element the block means.
        el = min(inner, key=lambda e: abs((e.sourceline or 0) - v["line"]))
        used.add(id(el))
        el["data-copy-id"] = bid
        el["data-copy-orig"] = norm(text)
        if note:
            el["data-copy-note"] = note
        if v["mine"]:
            el["data-copy-mine"] = ""
            mine.append(bid)
        tagged += 1
        return True

    for bid, v in body_want.items():
        if claim(bid, v["text"], v, v["note"]):
            continue
        # a few deck entries join two adjacent elements with " / " or " — "
        parts = re.split(r"\s+(?:/|—)\s+", v["text"])
        if len(parts) > 1 and all(claim(f"{bid}--{i+1}", p, v, v["note"] if i == 0 else "")
                                  for i, p in enumerate(parts)):
            continue
        missed.append(bid)

    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    overrides = """
/* --- copy editor overrides (not part of the site) --- */
details > summary { cursor: default; }
.mobile-book { display: none !important; }
html { scroll-behavior: auto; }
[data-copy-id] { outline-offset: 3px; border-radius: 2px; transition: background .12s, box-shadow .12s; }
a[data-goto]:not([data-copy-id]) { cursor: pointer; }
a[data-goto]:not([data-copy-id]):hover { outline: 2px solid #3a7d6c; outline-offset: 3px; border-radius: 2px; }
a[data-external]:not([data-copy-id]):hover { outline: 2px dashed #9aa0aa; outline-offset: 3px; border-radius: 2px; }
[data-copy-id]:hover { background: rgba(217,131,36,.10); box-shadow: 0 0 0 3px rgba(217,131,36,.10); cursor: text; }
[data-copy-id]:focus { outline: 2px solid #d98324; background: rgba(217,131,36,.06); }
[data-copy-id].is-changed { background: rgba(58,125,108,.10); box-shadow: -10px 0 0 0 #3a7d6c; }
[data-copy-id].is-changed:hover { background: rgba(58,125,108,.16); }
/* a cleared block stays clickable, so it can be restored with Esc */
[data-copy-id].is-empty { display: inline-block; min-width: 12em; min-height: 1.4em; }
[data-copy-id].is-empty::before {
  content: "Removed. Esc restores it."; font: italic 13px/1.4 -apple-system, BlinkMacSystemFont, sans-serif;
  color: #8d96a5; pointer-events: none;
}
[data-copy-flag]::after {
  content: attr(data-copy-flag); font-family: ui-monospace, Menlo, monospace;
  font-size: 9px; letter-spacing: .08em; vertical-align: super;
  background: #d98324; color: #fff; padding: 1px 4px; margin-left: 6px;
  border-radius: 2px; user-select: none; cursor: help;
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
"""
    body = soup.body
    inner = body.decode_contents() if body else soup.decode()
    doc = (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
           f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
           f"<style>{css}{overrides}</style></head><body>{inner}</body></html>")
    ids = [el["data-copy-id"] for el in soup.find_all(attrs={"data-copy-id": True})]
    return doc, meta, ids, mine, missed


print("→ building pages")
pages_data = []
total_tagged, total_mine, all_missed = 0, 0, []

for key, path, label in PAGES:
    doc, meta, ids, mine, missed = build_page(path, key)
    n = len(ids)
    pages_data.append({"key": key, "label": label, "group": "Pages",
                       "srcdoc": doc, "meta": meta, "blocks": n, "ids": ids, "mine": mine})
    total_tagged += n
    total_mine += len(mine)
    all_missed += missed
    print(f"   {label}: {n} editable blocks, {len(mine)} already yours"
          + (f"  ({len(missed)} unmatched)" if missed else ""))

print(f"→ {total_tagged} editable blocks total, {total_mine} already yours; "
      f"{len(all_missed)} deck blocks unmatched")
if all_missed:
    print("   unmatched:", ", ".join(sorted(all_missed)[:40]))

(Path(__file__).parent / "pages.json").write_text(json.dumps(pages_data))
print(f"→ wrote pages.json ({(Path(__file__).parent / 'pages.json').stat().st_size//1024} KB)")
