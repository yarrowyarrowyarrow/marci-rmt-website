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

Read them with the `ArtifactData` tool (`list` on the `edits` collection), write
each block back into the HTML, then update the matching deck entries (new text,
a `YOURS` line, and drop any `NOTE:` the edit resolved) so the next build
still matches.
