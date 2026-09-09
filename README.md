# folio

A small static site generator for long-form notes and reports. It is the
build pipeline of [dump](https://dump.wilbeibi.com) pulled out into its own
repository, with the saait + smu stage replaced by [md4c](https://github.com/mity/md4c)
and one Python file, so the same framework can run any number of sites (work
notes, a second research site, a wiki) without carrying dump's content or
writing contract along.

What stays from dump: the look (system font, 46rem measure, light/dark from the
OS), no front matter, categories as directories, git-derived timestamps, flat
URLs, bilingual pages by filename suffix, sortable tables, the `.viz` chart
convention, revision marks and errata blocks. What is new: real Markdown
tables and fenced code, footnotes, mermaid, MathJax, hover popups (link
previews, glossary terms, footnotes), per-page assets for embedded animations,
a link checker, and a dev server.

## Requirements

- Python ≥ 3.11 (stdlib only)
- md4c: `sudo pacman -S md4c` on Arch, `brew install md4c` on macOS
- git, optional: created/updated timestamps come from the site's history

## Quickstart

    mkdir -p ~/src/worknotes/pages/notes && cd ~/src/worknotes
    cp ~/src/folio/example/site.toml ~/src/folio/example/Makefile .   # edit name/url/categories
    ~/src/folio/folio new notes first-note --title "First note"
    make            # -> output/
    make serve      # http://127.0.0.1:8000/
    make watch      # rebuild on save
    make check      # build, fail on dead links / anchors / unresolved [[terms]]

`example/` is a complete site that uses every feature; `make example` in this
directory builds it. Read `example/pages/notes/2026-09-08-hello-folio.md`
first: it is the authoring reference in one page.

## A site

    site.toml                       name, url, languages, categories
    pages/<category>/YYYY-MM-DD-slug.md         a page
    pages/<category>/YYYY-MM-DD-slug.<lang>.md  its translation
    pages/<category>/YYYY-MM-DD-slug/           its assets -> /slug/
    static/                         copied to output root (favicon, images)
    theme/                          optional overrides of framework theme files
    output/                         generated, gitignored, point the web server here

The filesystem is the metadata. Category is the directory, date is the
filename prefix, language is the filename suffix, title is the first `# `
line, description is the first paragraph, created/updated come from git
(`--follow`, and renames do not count as updates). Output is flat:
`slug.html`, `slug.en.html`, so moving a page between categories never breaks
a link. A filename starting with `_` is a draft and is skipped.

### site.toml

```toml
name = "dump"
description = "research dumps"
url = "https://dump.wilbeibi.com"   # needed for the atom feed
author = "wilbeibi"
lang = "en"            # default for categories
glossary = "glossary"  # slug of the page whose h2/h3 define [[terms]]
toc_min = 3            # toc = true categories get a TOC from this many h2s

[[category]]           # the first category is the landing page (/)
dir = "reports"
title = "reports"
description = "shown under the index heading"
lang = "zh"
translations = ["en"]  # reports/x.en.md builds x.en.html; nav shows 中文 · EN
atom = true            # included in /atom.xml
toc = false
math = true            # $…$ spans; off if a category writes many bare $ signs
glossary = "glossary"  # per-category override

[[category]]
dir = "ideas"          # index at /ideas.html, English, untranslated

[langs.en]             # labels; en and zh have defaults
name = "EN"
updated = "updated"
missing = "no {name} version yet"
```

## What you write, what you get

| you write | you get |
|---|---|
| `# Title` first line | page title; the line is removed from the body |
| first paragraph | `<meta description>`, index summary, link-preview text |
| `## Heading` | `id` = heading text with spaces as `-` (CJK kept), deep-linkable, dedup'd |
| `[text](other.html#Heading)` | link checked at build time; hover shows the target's heading + first paragraph |
| `[[Term]]`, `[[Term\|label]]` | link to the glossary page's `## Term` with a hover popup of its first paragraph; `[[slug]]` / `[[slug#Heading]]` link pages |
| `text[^n]` + `[^n]: note` | superscript with hover popup, endnote list at the bottom |
| GFM `\| table \|` | sortable table (click a header), stays within the reading column and scrolls when needed |
| `<div class="t"><table>…` | the same, for hand-written tables |
| `<div class="t wide"><table>…` | explicitly let a hand-written comparison table break out on wide screens |
| ```` ```lang ```` fences | `<pre><code class="language-lang">` (no highlighting, by design) |
| ```` ```mermaid ```` | diagram rendered client-side, theme follows the OS, source is the no-JS fallback |
| `$x$`, `$$…$$` | MathJax (tex-svg), loaded only on pages with math; `$5` and `$10` in prose are left alone |
| `<div class="viz">…<script>` | any raw HTML + inline script; page assets live in `pages/<cat>/<date>-<slug>/` and are served at `/slug/` |
| `<details>` | collapsible, Markdown inside works |
| `> [!NOTE]`, `[!IMPORTANT]`, `[!WARNING]` | a restrained callout; an optional title follows the marker |
| `~~text~~`, `<del>` | strikethrough |
| `<ins datetime="…" data-d="MM-DD">` | revision mark: left colour bar and margin date badge |
| `<div class="errata">` | greyed correction log at the bottom |
| `---` | `<hr>` |

Everything JS-related is progressive enhancement: the page is complete
without it. Each page loads `folio.js` (≈7 KB: sorting, popups, minimap,
mermaid bootstrap, helpers) and, only when used, `charts.js`, mermaid, MathJax.

Callouts intentionally have only three meanings: `NOTE` adds context,
`IMPORTANT` states a conclusion or invariant, and `WARNING` names a risk or
failure mode. Other `[!TYPE]` markers remain ordinary blockquotes.

### Supporting material

Keep raw scripts, result JSON, and other publishable evidence in the page's
matching asset directory. Link the files explicitly from the page rather than
asking Folio to infer a references section:

```
pages/notes/2026-09-09-report.md
pages/notes/2026-09-09-report/probe.sh
pages/notes/2026-09-09-report/results.json
```

```markdown
## Materials

- [Probe script](report/probe.sh)
- [Raw results](report/results.json)
```

The files are copied verbatim to `/report/`; `folio check` verifies explicit
links into page asset directories. Everything in such a directory is public,
so it must not contain credentials or private raw data.

### Embedded animations

A page script gets `window.folio`:

```js
folio.onVisible(el, fn, {repeat, leave, threshold})  // start when scrolled into view
folio.reducedMotion   // true when the OS asks for no animation: draw one frame
folio.dark()          // current theme;  folio.onThemeChange(fn)
folio.css('--s1', el) // read a palette colour off the page
```

`example/pages/notes/2026-09-08-hello-folio/anim.js` is the pattern: start on
view, pause off view, static under reduced motion, colours from the CSS
palette so light and dark both work.

### Self-hosting mermaid and MathJax

Pages that need them load pinned versions from jsDelivr (see `vendor.txt`).
`folio vendor` downloads them into `theme/vendor/` (gitignored); from then on
the build copies only the ones a site actually uses into `output/vendor/`, so
a tailnet-only site works without internet.

## Theme

`theme/` holds `style.css`, `folio.js`, `charts.js`, `favicon.svg`, and the
templates `page.html`, `index.html`, `index-item.html`, `atom.xml`,
`atom-item.xml` with `{{var}}` placeholders. A site can put a file of the same
name in its own `theme/` to replace it, or a `theme/site.css` to append CSS
without replacing the base. Vars available to `page.html`: `lang site_name
title description head nav meta toc content pops footer`; to `index.html`:
`lang site_name title description head brand secnav items footer`.

## Deploying

`output/` is plain files: point Caddy, nginx or `python3 -m http.server` at
it. dump keeps its Caddy vhost; a work machine can use `make serve`.

## Migrating dump onto folio

Not done yet; the content already builds cleanly through folio (75 pages, 3
indexes, same file list as today). To switch:

1. Add a `site.toml` to `~/dump` (reports zh+en with atom and glossary
   `glossary`; ideas en; investment en+zh with glossary `invest-glossary`) and
   replace the `Makefile` with `example/Makefile` plus the `translate` targets.
2. `folio check --root ~/dump` lists 33 dead in-page anchors that the old
   pipeline never checked (links written as lowercase GitHub-style slugs, or
   headings edited after the link). Fix or drop them.
3. Delete `mkpages.sh`, `templates/`, `config.cfg`, `statics/`, `style.css`
   (now in the theme; put dump-only rules in `theme/site.css`). Keep
   `translate.sh`, it only reads `pages/`.
4. Update `AGENTS.md`: tables and fences are plain Markdown now, blank lines
   inside HTML blocks are fine, `~~` works, footnotes and `[[terms]]` exist.
5. `make` and diff `output/` against the previous build; the differences are
   `&quot;` escaping, properly closed `<p>` tags, and percent-encoded anchors.

## Deliberately absent

Search, tags, comments, pagination, syntax highlighting, a plugin system,
any build dependency beyond md4c and Python. Add a feature only when a page
needs it, and make it light up from the Markdown rather than from config.
