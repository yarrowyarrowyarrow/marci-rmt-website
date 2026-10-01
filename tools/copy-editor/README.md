# Copy editor build

Generates a single-file WYSIWYG editor for the site's copy: every page rendered
exactly as it appears to visitors, with each block of text editable in place.
Published as a Claude artifact, where edits persist to the artifact's database
keyed by block id so they can be read back and merged into the HTML.

## Build

    pip install beautifulsoup4 pillow
    python3 tools/copy-editor/build_editor.py   # writes pages.json alongside itself
    python3 tools/copy-editor/build_shell.py    # writes copy-editor.html at repo root

`copy-editor.html` is generated and gitignored. It embeds every page plus
downscaled copies of the assets. Publish it as an artifact (declaring the `db`
capability) rather than committing it. This repo is served publicly by GitHub
Pages and the editor is an internal tool; `_config.yml` keeps this folder and
the copy deck out of the published site.

## How blocks are identified

`copy-deck.md` at the repo root is the source of block ids. Each `### <id>`
entry carries the block's current text, its source location (`file:line`), and
optionally a `NOTE:` (a review flag, shown as a tag in the editor) and a
`YOURS` line (text already in Marci's own words, shown with a green bar and
counted toward "In your words").

`build_editor.py` matches each block's text against the parsed HTML (whitespace
normalised, inline tags flattened) and tags the innermost matching element with
`data-copy-id`. When the same words appear twice on a page, the deck's line
number picks the right one.

A block that stops matching (because the HTML changed but the deck didn't, or
vice versa) is reported as unmatched at build time rather than silently
mistagged. Keep that count at zero.

## Merging edits back

Edits live in the artifact db under `edits/<page-key>` as
`{blocks: {<block-id>: "new text"}, updatedAt}`. Two keys are reserved:
`__title` and `__description` hold the page's `<title>` and meta description,
which are edited in the chrome rather than on the page. An empty string means
the block was cleared: remove that element from the page.

`merge_edits.py` does the merge:

1. Save the edits: `ArtifactData` `list` on the `edits` collection with an
   `out_dir`. That writes one JSON file per page under `<out_dir>/edits/`.
   Keep that folder as the backup; fix typos in a copy of it, not the original.
2. `python3 tools/copy-editor/merge_edits.py <copy-of-edits-folder>`
   rewrites only the edited elements' text (the rest of each file is
   untouched), keeps inline markup that still fits (the italic tail of a
   headline, a `<br>` before it, links and bold around words still present),
   removes cleared blocks, and marks merged blocks `YOURS` in the deck.
3. After any hand edits to the pages, run
   `python3 tools/copy-editor/merge_edits.py --refresh --prune` to update the
   deck's line numbers and drop blocks that are no longer on the page.
4. Rebuild (0 unmatched), republish the editor to the same URL, then delete
   the merged documents from the artifact db so the editor starts clean from
   the new wording.
