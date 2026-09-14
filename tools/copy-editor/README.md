# Copy editor build

Generates a single-file WYSIWYG editor for the site's copy: every page rendered
exactly as it appears to visitors, with each block of text editable in place.
Published as a Claude artifact, where edits persist to the artifact's database
keyed by block id so they can be read back and merged into the HTML.

## Build

    pip install beautifulsoup4 pillow
    python3 tools/copy-editor/build_editor.py   # writes pages.json alongside itself
    python3 tools/copy-editor/build_shell.py    # writes copy-editor.html at repo root

`copy-editor.html` is generated and gitignored — it embeds every page plus
downscaled copies of the assets, so it runs about 1 MB. Publish it as an
artifact rather than committing it; this repo is served publicly by GitHub
Pages and the editor is an internal tool.

## How blocks are identified

`copy-deck.md` at the repo root is the source of block ids. Each `### <id>`
entry carries the block's current text, its source location, and any review
note. `build_editor.py` matches that text against the parsed HTML — whitespace
normalised, inline tags flattened, smallest matching subtree wins — and tags
the element with `data-copy-id`.

A block that stops matching (because the HTML changed but the deck didn't, or
vice versa) is reported as unmatched at build time rather than silently
mistagged. Keep that count at zero.

## Merging edits back

Edits live in the artifact db under `edits/<page-key>` as
`{blocks: {<block-id>: "new text"}, updatedAt}`. Two keys are reserved:
`__title` and `__description` hold the page's `<title>` and meta description,
which are edited in the chrome rather than on the page.

Read them with the Artifact tool's `read_db` action, then write each block back
to the element carrying that `data-copy-id`.
