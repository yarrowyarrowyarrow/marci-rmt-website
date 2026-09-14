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

ROOT = Path("/home/user/marci-rmt-website")
OUT = ROOT / "copy-editor.html"

PAGES = [
    ("index",           "index.html",        "Home"),
    ("about",           "about.html",        "About"),
    ("services",        "services.html",     "In-Home Services"),
    ("events",          "events.html",       "Event Massage"),
    ("areas",           "areas.html",        "Areas Served"),
    ("first-visit",     "first-visit.html",  "Your First Visit"),
    ("faq",             "faq.html",          "Policies & FAQ"),
    ("contact",         "contact.html",      "Contact"),
    ("404",             "404.html",          "404 page"),
]
CONDITIONS = [
    ("tension-headaches",  "Tension headaches"),
    ("neck-shoulder",      "Neck & shoulder pain"),
    ("low-back-pain",      "Low back pain"),
    ("stress-sleep",       "Stress & sleep"),
    ("tmj",                "TMJ & jaw tension"),
    ("frozen-shoulder",    "Frozen shoulder"),
    ("sciatica",           "Sciatica & piriformis"),
    ("pregnancy",          "Pregnancy massage"),
    ("post-surgical",      "Post-surgical recovery"),
    ("repetitive-strain",  "Repetitive strain"),
    ("plantar-fasciitis",  "Plantar fasciitis"),
    ("maintenance",        "General maintenance"),
]

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
    """Read copy-deck.md -> {block_id: {'text':..., 'note':..., 'src':...}}"""
    deck = {}
    txt = (ROOT / "copy-deck.md").read_text(encoding="utf-8")
    for chunk in re.split(r"^### ", txt, flags=re.M)[1:]:
        lines = chunk.split("\n")
        bid = lines[0].strip()
        src, note, body = "", "", []
        for ln in lines[1:]:
            if ln.startswith("---") or ln.startswith("#"):
                break
            if ln.startswith("`") and not src:
                src = ln.strip("` ")
            elif ln.startswith("NOTE:"):
                note = ln[5:].strip()
            elif ln.strip():
                body.append(ln.strip())
        if bid and body:
            deck[bid] = {"text": " ".join(body), "note": note, "src": src}
    return deck


DECK = parse_deck()
print(f"→ parsed {len(DECK)} deck blocks")


# ------------------------------------------------------------ page build
def build_page(html_path, page_key, rel_prefix=""):
    """Return (srcdoc_html, meta, tagged_count, missed_ids)."""
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

    # links are inert here; the page switcher navigates
    for a in soup.find_all("a"):
        a["href"] = "javascript:void(0)"
        a["tabindex"] = "-1"

    # every FAQ answer visible at rest
    for d in soup.find_all("details"):
        d["open"] = ""

    # ---- tag editable blocks by matching deck text
    want = {bid: v for bid, v in DECK.items()
            if v["src"].split(":")[0].endswith(html_path.split("/")[-1])
            or (rel_prefix and "conditions/" in v["src"] and page_key in v["src"])}

    # meta blocks live in the chrome, not the page body
    body_want = {b: v for b, v in want.items()
                 if not re.search(r"meta-(title|description)|og-description", b)}

    # <br> and inline <em> must read as word breaks, so join with a space
    candidates = [e for e in soup.find_all(TAGGABLE) if e.get_text(strip=True)]
    index = {}
    for e in candidates:
        index.setdefault(norm(e.get_text(" ")), []).append(e)

    tagged, missed = 0, []
    used = set()

    def claim(bid, text, note):
        nonlocal tagged
        matches = [e for e in index.get(norm(text), []) if id(e) not in used]
        if not matches:
            return False
        # smallest subtree = the element that actually owns this text
        el = min(matches, key=lambda e: len(list(e.descendants)))
        used.add(id(el))
        el["data-copy-id"] = bid
        el["data-copy-orig"] = norm(text)
        if note:
            el["data-copy-note"] = note
        tagged += 1
        return True

    for bid, v in body_want.items():
        if claim(bid, v["text"], v["note"]):
            continue
        # a few deck entries join two adjacent elements with " / " or " — "
        parts = re.split(r"\s+(?:/|—)\s+", v["text"])
        if len(parts) > 1 and all(claim(f"{bid}--{i+1}", p, v["note"] if i == 0 else "")
                                  for i, p in enumerate(parts)):
            continue
        missed.append(bid)

    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    overrides = """
/* --- copy editor overrides (not part of the site) --- */
.tab-pane { display: block !important; margin-bottom: 40px; }
.tab-row { pointer-events: none; }
details > summary { cursor: default; }
.mobile-book { display: none !important; }
html { scroll-behavior: auto; }
[data-copy-id] { outline-offset: 3px; border-radius: 2px; transition: background .12s, box-shadow .12s; }
[data-copy-id]:hover { background: rgba(217,131,36,.10); box-shadow: 0 0 0 3px rgba(217,131,36,.10); cursor: text; }
[data-copy-id]:focus { outline: 2px solid #d98324; background: rgba(217,131,36,.06); }
[data-copy-id].is-changed { background: rgba(58,125,108,.10); box-shadow: -10px 0 0 0 #3a7d6c; }
[data-copy-id].is-changed:hover { background: rgba(58,125,108,.16); }
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
    return doc, meta, tagged, missed


print("→ building pages")
pages_data = []
total_tagged, all_missed = 0, []

for key, path, label in PAGES:
    doc, meta, n, missed = build_page(path, key)
    pages_data.append({"key": key, "label": label, "group": "Main pages",
                       "srcdoc": doc, "meta": meta})
    total_tagged += n
    all_missed += missed
    print(f"   {label}: {n} editable blocks" + (f"  ({len(missed)} unmatched)" if missed else ""))

for key, label in CONDITIONS:
    doc, meta, n, missed = build_page(f"conditions/{key}.html", key, rel_prefix="../")
    pages_data.append({"key": f"cond-{key}", "label": label, "group": "What I treat",
                       "srcdoc": doc, "meta": meta})
    total_tagged += n
    all_missed += missed
    print(f"   {label}: {n} editable blocks" + (f"  ({len(missed)} unmatched)" if missed else ""))

print(f"→ {total_tagged} editable blocks total; {len(all_missed)} deck blocks unmatched")
if all_missed:
    print("   unmatched:", ", ".join(sorted(all_missed)[:40]))

(Path(__file__).parent / "pages.json").write_text(json.dumps(pages_data))
print(f"→ wrote pages.json ({(Path(__file__).parent / 'pages.json').stat().st_size//1024} KB)")
