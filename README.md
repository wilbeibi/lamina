# Lamina

Publish long-form Markdown as a plain static site without front matter or a
CMS. Lamina derives page metadata from source paths and content. It writes
ordinary files you can serve anywhere.

It is for personal notes, research reports, and small documentation sites that
value durable source files and a restrained reading layout. It is not a blog
platform, CMS, search service, or plugin host.

## Start a site

Lamina needs [uv](https://docs.astral.sh/uv/) and Python 3.11 or later.
Install the `lamina` command onto your PATH:

```sh
uv tool install git+https://github.com/wilbeibi/lamina
```

The repository is still private, so use
`git+ssh://git@github.com/wilbeibi/lamina` until it is public. `uvx --from`
either URL runs it without installing. Git is optional but supplies created and
updated timestamps when available.

Then scaffold a site in another directory:

```sh
lamina init ~/src/worknotes
cd ~/src/worknotes && lamina build
```

`init` writes `site.toml`, `pages/notes/`, and a first page; add categories by
editing `site.toml` and creating their directories, or run `lamina new` to
write a page in one. Edit `site.toml` before publishing, especially its `name`,
`description`, `url`, and category definitions. The build writes the site to
`output/`.

For a local preview, rebuild and serve on the loopback interface:

```sh
lamina serve
# http://127.0.0.1:8000/
```

Use `lamina watch` to rebuild after source changes. Use `lamina check` in CI or
before publishing; it fails on build warnings, including bad links, missing
anchors, and unresolved wiki links. Run `lamina --help` for the full interface.

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

A page whose slug is `index` (for example `pages/notes/2026-09-08-index.md`)
is served at `/` instead of the index list. The list moves to `/<dir>.html` and
stays reachable from the page navigation, so the site reads as a single page at
the root. Without such a page the landing page is an index of the first
category's pages.

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

Lamina uses GitHub-flavored Markdown. It supports tables, fenced and indented
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

Lamina supplies a system-font layout with OS-controlled light and dark themes.
To override a framework file, add a same-named file under the site's `theme/`:
`style.css`, `lamina.js`, `favicon.svg`, `page.html`, `index.html`,
`index-item.html`, `atom.xml`, or `atom-item.xml`. Add `theme/site.css` to
append site-specific CSS without replacing the base stylesheet.

`output/` contains only static files. Serve it with Caddy, nginx, or any
static-file host.

Mermaid and MathJax normally load from their pinned jsDelivr versions. To
self-host them, run this before building:

```sh
lamina vendor
```

The files land in the site's `theme/vendor/` (add it to `.gitignore`), and
the build copies only the ones the site uses into `output/vendor/`.

## Limits

Lamina deliberately does not provide search, tags, comments, pagination,
syntax highlighting, or a plugin system. It also does not manage hosting or
deployments. Add a feature only when the Markdown and generated files remain
easy to inspect and move.
