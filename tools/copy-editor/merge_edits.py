#!/usr/bin/env python3
"""Merge copy-editor edits back into the site's HTML and the copy deck.

    python3 tools/copy-editor/merge_edits.py EDITS_DIR     # merge, then refresh the deck
    python3 tools/copy-editor/merge_edits.py --refresh      # only refresh deck line numbers
    python3 tools/copy-editor/merge_edits.py --refresh --prune
                                    # ...and drop deck blocks whose text is no longer on the page

EDITS_DIR holds one JSON file per page key (index.json, about.json, ...), as
saved by the ArtifactData tool's `list` with `out_dir` on the `edits`
collection: {"blocks": {block_id: text, "__title": ..., "__description": ...},
"updatedAt": ...}.

Each block's element is found the same way build_editor.py finds it (deck
text, innermost match, nearest deck line). Only that element's text changes,
so the rest of the file keeps its formatting. Inline markup is carried over
where it still fits: <em>/<strong>/<a> around words that are still there,
the italic accent at the end of a headline, and a <br> before it. An empty
edit removes the element. Merged blocks are marked YOURS in the deck and
lose their review NOTE, since the wording is now Marci's.
"""
import html
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[2]
DECK = ROOT / "copy-deck.md"
INLINE = ("em", "strong", "a", "b", "i")
HEADINGS = ("h1", "h2", "h3", "h4")


def norm(s):
    # identical to build_editor.py
    s = re.sub(r"\s+", " ", s or "").strip()
    return re.sub(r"\s+([,.;:!?%])", r"\1", s)


def page_file(key):
    return "index.html" if key == "index" else f"{key}.html"


# ------------------------------------------------------------------ deck
def read_deck():
    """Split the deck into its raw text and an ordered list of block entries."""
    text = DECK.read_text(encoding="utf-8")
    entries = []
    for m in re.finditer(r"^### (\S+)\n(.*?)(?=^### |^---|\Z)", text, flags=re.M | re.S):
        lines = [ln for ln in m.group(2).split("\n") if ln.strip()]
        src = lines[0].strip("` ") if lines and lines[0].startswith("`") else ""
        e = {"id": m.group(1), "span": m.span(), "src": src,
             "file": src.split(":")[0], "line": int((re.search(r":(\d+)", src) or [0, 0])[1]),
             "yours": any(ln.strip() == "YOURS" for ln in lines),
             "note": next((ln for ln in lines if ln.startswith("NOTE:")), ""),
             "text": " ".join(ln.strip() for ln in lines[1:]
                              if ln.strip() != "YOURS" and not ln.startswith("NOTE:"))}
        entries.append(e)
    return text, entries


def render_entry(e):
    out = [f"### {e['id']}", f"`{e['file']}:{e['line']}`"]
    if e["yours"]:
        out.append("YOURS")
    if e["note"]:
        out.append(e["note"])
    out.append(e["text"])
    return "\n".join(out) + "\n\n"


def write_deck(text, entries, drop=()):
    for e in sorted(entries, key=lambda e: e["span"][0], reverse=True):
        a, b = e["span"]
        text = text[:a] + ("" if e["id"] in drop else render_entry(e)) + text[b:]
    DECK.write_text(re.sub(r"\n{3,}", "\n\n", text), encoding="utf-8")


# ------------------------------------------------------------ locating
def find_element(soup, text, line):
    want = norm(text)
    matches = [e for e in soup.find_all(True) if norm(e.get_text(" ")) == want]
    ids = {id(e) for e in matches}
    inner = [e for e in matches if not any(id(d) in ids for d in e.find_all(True))]
    if not inner:
        return None
    return min(inner, key=lambda e: abs((e.sourceline or 0) - line))


def offsets(src):
    starts, n = [0], 0
    for ln in src.split("\n"):
        n += len(ln) + 1
        starts.append(n)
    return starts


def element_span(src, starts, el):
    """(start of start tag, end of start tag, start of end tag, end of end tag)."""
    s = starts[el.sourceline - 1] + el.sourcepos
    i, quote = s, None
    while True:                                   # end of the start tag, quotes respected
        c = src[i]
        if quote:
            quote = None if c == quote else quote
        elif c in "\"'":
            quote = c
        elif c == ">":
            break
        i += 1
    open_end = i + 1
    depth = 1
    for m in re.compile(rf"<(/?){el.name}\b[^>]*>", re.I).finditer(src, open_end):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return s, open_end, m.start(), m.end()
    raise ValueError(f"no closing </{el.name}> for element on line {el.sourceline}")


def open_tag(src, starts, el):
    s, oe, _, _ = element_span(src, starts, el)
    return src[s:oe]


# ------------------------------------------------------------ rebuilding
def rebuild(src, starts, el, new_text):
    """New inner HTML for `el`: the edited text, with the original inline markup
    re-applied where it still fits. Returns (inner_html, notes)."""
    notes = []
    _, oe, ce, _ = element_span(src, starts, el)
    old_inner = src[oe:ce]
    lead = re.match(r"\s*", old_inner).group(0)
    trail = re.search(r"\s*$", old_inner).group(0)
    old_text = norm(el.get_text(" "))

    # the edited text as segments, so later wraps never match inside markup
    segs = [["t", new_text]]

    def wrap(start_char, end_char, tag_open, tag_name):
        # wrap new_text[start:end] (character offsets into the plain text)
        out, pos = [], 0
        for kind, s in segs:
            if kind == "h":
                out.append([kind, s]); continue
            a, b = pos, pos + len(s)
            if a <= start_char and end_char <= b:
                out += [["t", s[:start_char - a]], ["h", tag_open], ["t", s[start_char - a:end_char - a]],
                        ["h", f"</{tag_name}>"], ["t", s[end_char - a:]]]
            else:
                out.append([kind, s])
            pos = b
        segs[:] = [x for x in out if x[1]]

    def plain():
        return "".join(s for k, s in segs if k == "t")

    for child in [c for c in el.find_all(INLINE)]:
        t = norm(child.get_text(" "))
        if not t:
            continue
        tag_open = open_tag(src, starts, child)
        i = plain().find(t)
        if i >= 0:
            wrap(i, i + len(t), tag_open, child.name)
            continue
        words = plain().split(" ")
        if child.name == "em" and old_text.endswith(t) and len(words) > 1:
            k = min(len(t.split()), len(words) - 1)          # the headline's italic tail
        elif child.name == "em" and el.name in HEADINGS and len(words) > 1:
            k = 1                                            # keep the heading's accent on its last word
        else:
            notes.append(f"<{child.name}> around \"{t}\" dropped: those words are gone")
            continue
        tail = " ".join(words[-k:])
        i = len(plain()) - len(tail)
        wrap(i, len(plain()), tag_open, child.name)

    inner = "".join(html.escape(s, quote=False) if k == "t" else s for k, s in segs)
    # a <br> that sat right before the italic tail stays there
    br = el.find("br")
    if br is not None:
        nxt = br.find_next_sibling()
        if nxt is not None and nxt.name == "em":
            tag_open = open_tag(src, starts, nxt)
            if tag_open in inner:
                inner = re.sub(r"\s*" + re.escape(tag_open), "<br />" + tag_open, inner, count=1)
            else:
                notes.append("<br> dropped")
    return lead + inner + trail, notes


def removal_span(src, s, e):
    """Widen [s, e) to whole lines when the element sits alone on its line."""
    ls = src.rfind("\n", 0, s) + 1
    le = src.find("\n", e)
    le = len(src) if le < 0 else le
    if not src[ls:s].strip() and not src[e:le].strip():
        return ls, min(le + 1, len(src))
    return s, e


# ------------------------------------------------------------ commands
def merge(edits_dir):
    deck_text, entries = read_deck()
    by_id = {e["id"]: e for e in entries}
    removed = set()
    for f in sorted(Path(edits_dir).glob("*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        blocks = dict((doc.get("data", doc) or {}).get("blocks", {}))
        page = page_file(f.stem)
        path = ROOT / page
        src = path.read_text(encoding="utf-8")
        soup = BeautifulSoup(src, "html.parser")
        starts = offsets(src)
        changes = []                                  # (start, end, replacement)

        title, desc = blocks.pop("__title", None), blocks.pop("__description", None)
        if title is not None:
            m = re.search(r"(<title>)(.*?)(</title>)", src, re.S)
            changes.append((m.start(2), m.end(2), html.escape(title, quote=False)))
        if desc is not None:
            m = re.search(r'(<meta name="description" content=")([^"]*)(")', src)
            changes.append((m.start(2), m.end(2), html.escape(desc, quote=True)))

        for bid, new in blocks.items():
            e = by_id.get(bid)
            if e is None or e["file"] != page:
                print(f"  ?? {page}: {bid} is not a block on this page, skipped")
                continue
            el = find_element(soup, e["text"], e["line"])
            if el is None:
                print(f"  ?? {page}: {bid} not found (deck text no longer matches the page), skipped")
                continue
            s, oe, ce, end = element_span(src, starts, el)
            new = norm(new)
            if not new:
                a, b = removal_span(src, s, end)
                changes.append((a, b, ""))
                removed.add(bid)
                print(f"  -  {page}: {bid} removed")
                continue
            inner, notes = rebuild(src, starts, el, new)
            changes.append((oe, ce, inner))
            e["text"], e["yours"], e["note"] = new, True, ""
            for n in notes:
                print(f"  !  {page}: {bid}: {n}")

        for a, b, rep in sorted(changes, reverse=True):
            src = src[:a] + rep + src[b:]
        path.write_text(src, encoding="utf-8")
        print(f"{page}: merged {len(changes)} change(s)")

    write_deck(deck_text, entries, drop=removed)
    refresh()


def refresh(prune=False):
    """Re-find every deck block on its page, update its line number, and list
    (or with prune, drop) blocks whose text is no longer on the page."""
    deck_text, entries = read_deck()
    soups = {}
    missing = []
    # og-description first: "description" alone would also match its id
    meta_tag = {"og-description": '<meta property="og:description"', "title": "<title>",
                "description": '<meta name="description"'}
    for e in entries:
        kind = next((k for k in meta_tag if e["id"].endswith(k)), None)
        if "-meta-" in e["id"] or kind == "og-description":
            src = (ROOT / e["file"]).read_text(encoding="utf-8")
            i = src.find(meta_tag[kind]) if kind else -1
            if i >= 0:
                e["line"] = src.count("\n", 0, i) + 1
            continue
        if e["file"] not in soups:
            soups[e["file"]] = BeautifulSoup((ROOT / e["file"]).read_text(encoding="utf-8"), "html.parser")
        el = find_element(soups[e["file"]], e["text"], e["line"])
        if el is None:
            missing.append(e["id"])
        else:
            e["line"] = el.sourceline
    write_deck(deck_text, entries, drop=set(missing) if prune else ())
    if missing:
        print(("pruned" if prune else "not found on their page") + f": {', '.join(missing)}")
    print(f"deck refreshed: {len(entries) - (len(missing) if prune else 0)} blocks")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--refresh":
        refresh(prune="--prune" in args)
    elif len(args) == 1:
        merge(args[0])
    else:
        sys.exit(__doc__)
