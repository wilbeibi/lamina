# folio

Publish long-form Markdown as a plain static site without front matter or a
CMS. Folio derives page metadata from source paths and content. It writes
ordinary files you can serve anywhere.

It is for personal notes, research reports, and small documentation sites that
value durable source files and a restrained reading layout. It is not a blog
platform, CMS, search service, or plugin host.

## Start a site

Folio needs [uv](https://docs.astral.sh/uv/). The `folio` script requests
Python 3.11 or later and declares its dependencies inline, so uv creates and
reuses a cached environment on first run. Git is optional but supplies created
and updated timestamps when available.

From a checkout of this repository, create a site in another directory:

```sh
mkdir -p ~/src/worknotes/pages/notes ~/src/worknotes/pages/reports
cd ~/src/worknotes
cp /path/to/folio/example/site.toml .
/path/to/folio/folio new notes first-note --title "First note"
/path/to/folio/folio build
```

Edit `site.toml` before publishing, especially its `name`, `description`,
`url`, and category definitions. The build writes the site to `output/`.

For a local preview, rebuild and serve on the loopback interface:

```sh
/path/to/folio/folio serve
# http://127.0.0.1:8000/
```

Use `folio watch` to rebuild after source changes. Use `folio check` in CI or
before publishing; it fails on build warnings, including bad links, missing
anchors, and unresolved wiki links. Run `folio --help` for the full interface.

`example/` is a working site that exercises every supported feature:

```sh
make example
make check
```

## Site layout

```text
site.toml                                     site and category settings
pages/<category>/YYYY-MM-DD-slug.md            canonical page
pages/<category>/YYYY-MM-DD-slug.<lang>.md     translation
pages/<category>/YYYY-MM-DD-slug/              files served at /slug/
static/                                        copied to the output root
theme/                                         optional framework overrides
output/                                        generated site; point a web server here
```

The first `[[category]]` is the landing page at `/`; later categories become
`/<category>.html`. Canonical pages build as `/slug.html`; translations build
as `/slug.<lang>.html`. URLs stay flat when you move a page between categories.

The first `# ` heading becomes the page title and is removed from the body.
The first prose paragraph becomes the description used by indexes, metadata,
and link previews. A filename beginning with `_` is a draft and is skipped.

Here is a minimal configuration:

```toml
name = "worknotes"
description = "notes and reports"
url = "https://notes.example.com" # required for an Atom feed
author = "Your name"
lang = "en"
glossary = "glossary"              # page whose h2/h3 headings define [[terms]]

[[category]]
dir = "notes"
title = "notes"
description = "notes, plans, and reports"
atom = true
toc = true
```

See [example/site.toml](example/site.toml) for Chinese-canonical pages with
English translations and the remaining options.

## Write pages

Folio uses GitHub-flavored Markdown. It supports tables, fenced and indented
code, strikethrough, footnotes, collapsible sections, and raw HTML. Links are
checked during a build.

```markdown
# A page title

This first paragraph is the page description.

## A section

See [another page](other-page.html#A-section). Link a glossary term as
[[Term]] or [[Term|visible label]].

[^source]: Footnotes support Markdown; `^[an inline note]` works too.
```

Heading IDs replace spaces with `-`, preserve CJK characters, and are
deduplicated. Encode spaces in link URLs as `%20`.

The following features activate only when their Markdown appears:

| Source | Result |
|---|---|
| `\| table \|` | Sortable table that scrolls within the reading column. |
| A `mermaid` fenced block | Client-rendered Mermaid diagram with source as the no-JavaScript fallback. |
| `$x$` or `$$...$$` | MathJax SVG math; bare currency such as `$5` remains prose. |
| `> [!NOTE]`, `[!IMPORTANT]`, `[!WARNING]` | A callout for context, an invariant, or a risk. |
| `<div class="viz">…</div>` | A page-local visualization or script. |
| `<ins datetime="…" data-d="MM-DD">` | Revision mark with a date badge. |
| `<div class="errata">` | Correction log styling. |

Use a page asset directory for scripts, raw data, and other material you want
to publish:

```text
pages/notes/2026-09-09-report.md
pages/notes/2026-09-09-report/probe.sh
pages/notes/2026-09-09-report/results.json
```

Those files are copied verbatim to `/report/`. Link them explicitly from the
page. Do not place credentials or private source data in an asset directory.

## Theme and deployment

Folio supplies a system-font layout with OS-controlled light and dark themes.
To override a framework file, add a same-named file under the site's `theme/`:
`style.css`, `folio.js`, `favicon.svg`, `page.html`, `index.html`,
`index-item.html`, `atom.xml`, or `atom-item.xml`. Add `theme/site.css` to
append site-specific CSS without replacing the base stylesheet.

`output/` contains only static files. Serve it with Caddy, nginx, or any
static-file host.

Mermaid and MathJax normally load from their pinned jsDelivr versions. To
self-host them, run this from the Folio checkout before building:

```sh
/path/to/folio/folio vendor
```

Folio copies only the vendor files used by the site into `output/vendor/`.

## Limits

Folio deliberately does not provide search, tags, comments, pagination,
syntax highlighting, or a plugin system. It also does not manage hosting or
deployments. Add a feature only when the Markdown and generated files remain
easy to inspect and move.
