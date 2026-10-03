---
name: lamina
description: Write and publish pages on a lamina site, a Markdown directory with site.toml and pages/. Covers the layout, every site.toml key, the Markdown extensions (asides, footnotes, [[terms]], callouts, mermaid, math), when to use each annotation, and the commands. Use whenever editing such a site.
---

# Lamina

Lamina publishes a directory of Markdown as plain HTML: notes, research
reports, small documentation sites. No front matter: the filesystem carries the
metadata. It deliberately has no search, tags, comments, pagination,
plugins, options, or deployment.

Three commands, run in the site directory, non-interactive, warnings to
stderr as `lamina: ...`:

```sh
lamina           # build into public/; exit 1 if there were warnings
lamina serve     # build, serve http://127.0.0.1:8471/, rebuild on change
lamina links     # fetch hover previews for new external links (below)
```

There is no scaffolding command: a site is `site.toml` plus one Markdown file,
both shown below. Needs [uv](https://docs.astral.sh/uv/) and Python 3.11+
(`uv tool install git+https://github.com/wilbeibi/lamina`). Git is optional
and supplies created/updated dates. `example/` in the repository is a complete
site that uses every feature.

## Layout

```text
site.toml                                    settings (below)
pages/<category>/YYYY-MM-DD-slug.md          -> /slug.html
pages/<category>/YYYY-MM-DD-slug.<lang>.md   -> /slug.<lang>.html   translation
pages/<category>/YYYY-MM-DD-slug/            -> /slug/              page assets, copied verbatim
static/                                      -> /                   site assets
theme/<file>                                 overrides the built-in file of the same name
public/                                      the built site
```

- Category = directory, date = filename prefix, language = filename suffix.
  URLs are flat, so a slug must be unique across the site and moving a page
  between categories does not change its URL.
- Title = the first `# ` line (removed from the body). Description = the first
  paragraph outside callouts. Created/updated = git history of the file.
- The first category is the landing page at `/` and the Atom feed at
  `/atom.xml` (when `url` is set); other categories list at `/<dir>.html`. A
  page whose slug is `index` is served at `/` instead, and the first
  category's list moves to `/<dir>.html`.
- A page slugged `glossary` or `<x>-glossary` is its category's glossary (see
  Markdown); a category without one uses any glossary on the site.
- A page with three or more h2s gets a table of contents.
- A filename starting with `_` is a draft and is skipped.

## site.toml

Every key, with its default. Only `[[category]]` and its `dir` are required;
an unknown key is an error.

```toml
name = "site"
description = ""
url = ""                 # needed for the Atom feed and absolute links
footer = ""              # HTML appended to every footer: source link, license

[langs.zh]               # en is built in; every other language needs its UI strings
name = "中文"
updated = "更新"
missing = "暂无{name}版"
contents = "目录"         # TOC heading
pinned = "置顶"           # accessible pin label; English default: Pinned

[[category]]
dir = "notes"            # pages/notes/
title = "notes"          # default: dir
description = ""
lang = "en"              # language of the canonical pages
translations = []        # e.g. ["en"] for pages/notes/*.en.md
pinned = []              # e.g. ["glossary", "second-note"], canonical slugs in display order
```

Pinned pages appear first in their category's list, with 📌 before each title.
The remaining pages appear newest first, without duplicates. The Atom feed stays chronological.
Omit `pinned` or use `[]` for the usual date order.
Duplicate slugs or slugs without a published canonical page in that category fail the build.
Custom `theme/index-item.html` templates use `{{pin}}` to display the marker.

## Markdown

GitHub-flavored: tables, fenced code, strikethrough, footnotes, task lists,
`<details>`, raw HTML. Links are checked at build time; a dead link, a bad
`#anchor`, or an unresolved `[[term]]` is a warning.
Missing local media also warns: `src` on images, audio, video, and `<source>`, plus video `poster`.
Paths resolve against the built site, including page assets and `static/`; remote URLs and `srcset` are not checked.

```markdown
# Title

First paragraph: the description.

## A section

[another page](other.html#A-section) · [[Term]] · [[Term|label]] · note[^1]

[^1]: Footnotes show as sidenotes on wide screens and popups elsewhere.
```

Table footnotes use popups at every width. Click a footnote reference to show its endnote.

`^[~remark]` is an aside: an unnumbered inline note beside its words, in the
margin when wide, with no popup or endnote. Hovering it highlights its sentence
up to the aside, and hovering those words highlights the aside;
`[these words]^[~remark]` picks the words instead.

Heading ids are the heading text with spaces as `-`, CJK kept, duplicates
numbered without collisions. Each h2–h4 has a `#` permalink; copy its link to cite that section.
Encode a space in a URL as `%20`.

A glossary page defines `[[terms]]` two ways: each h2/h3 heading, and each
list item that opens with bold text, `- **Term**: definition`. An item gets an
id by the heading rule and previews its definition. It also answers to the
term without parentheticals, to each parenthetical, and to each ` / `
alternative: `**EPS (earnings per share)**` matches `[[EPS]]` and
`[[earnings per share]]`, and `**long / short**` matches `[[long]]`.

Features that turn on when a page uses them:

| Source | Result |
|---|---|
| pipe table | click a header to sort ascending, then descending; scrolls inside the column |
| fenced or indented code | subtle Copy text in the top-right corner on HTTPS or localhost |
| language-labelled code fence | syntax highlighting with bundled Prism |
| image outside a link or button | click, Enter, or Space to enlarge; Escape, Close, or backdrop to dismiss |
| ```` ```mermaid ```` | diagram rendered in the browser, source as fallback |
| `$x$`, `$$…$$` | Temml MathML; `$5` and `$5-$10` stay prose |
| `> [!NOTE]` / `[!IMPORTANT]` / `[!WARNING]` | callout |
| `> [!ASIDE] text` | untitled remark in the right margin when wide, inline otherwise |
| `<ins datetime="2026-09-13" data-d="09-13">` | revision mark with a date badge |

Image zoom fits the screen initially. Choose Full size to inspect the original image and scroll across large figures.

The Copy text briefly changes to Copied after copying.

Label code fences with `python`, `bash` (`sh`, `shell`), `javascript` (`js`),
`typescript` (`ts`), `markup` (`html`, `xml`, `svg`), `css`, `json`, `yaml` (`yml`),
`sql`, `go`, or `rust`. Prism is bundled locally, with light/dark colors and no plugins or language downloads.
Unlabelled or unsupported languages stay plain; without JavaScript, all code stays readable.
Mermaid fences still render as diagrams.

Table sorting recognizes complete numbers, optional signs, `$`, comma grouping, and a `K`/`M`/`B` or `%` suffix.
Signs can precede or follow `$` (`-$2` or `$-2`). Footnotes and asides do not affect the sort value.
Percentages sort by their displayed number. Numbers precede text in both directions; dates and mixed labels sort as text.
Inline dollar math cannot cross a backtick; use display math for TeX containing literal backticks.

Mermaid and Temml load from pinned jsDelivr URLs, only on pages that use them.
Math uses local system fonts, supplemented by Temml's small font file.
Page-defined global TeX macros also work in footnote previews.
TeX stays visible without JavaScript.

To self-host, save `mermaid.min.js`, `temml.min.js`, `Temml-Local.css`, and `Temml.woff2` in `theme/`.
The URLs are at the top of `lamina/build.py`.
The font sits beside the Temml CSS at the same URL prefix.
Keep the CSS and font together; pages then load the site's copies.

Outside links get a hover preview too. `lamina links` fetches each linked
page's title and description into `links.json` at the site root; commit it,
and rerun after adding links. Only new links are fetched; delete `links.json`
to refetch everything. The build only reads that file, so it never touches the
network. A link title, `[text](https://… "one line")`, replaces the fetched
description; private pages, PDFs, and sites that block the fetch get a popup
only if they have one.

## Writing annotations

Asides follow Ink & Switch's margin notes: about two per 1,000 words, never
two on one paragraph.

- `^[~…]`: a skippable remark about one sentence, such as a source, example,
  caveat, detail or pointer. One or two sentences that stand alone; aim for
  35 words, never over 60. Put it at the end of the sentence; use
  `[words]^[~…]` only to gloss a term.
- `> [!ASIDE]`: a remark about a whole paragraph or section, or one of 35–60
  words. Inline, a long remark splits the paragraph on a phone.
- Over 60 words, or code or a figure: body text or an appendix, with a
  short aside pointing to it.
- Anything the argument needs goes in the body; a gloss under 10 words
  goes in parentheses.
- `[^n]`: formal citations, or a source cited more than once.
- Callouts: only what the reader must not skip.
- Never an image in an aside, or a figure's source (use the caption).

## Theme

System fonts, light and dark by OS setting. Put a file named `style.css`,
`lamina.js`, `prism.js`, `favicon.svg`, `page.html`, `index.html`, `index-item.html`,
`atom.xml`, or `atom-item.xml` in `theme/` to replace the built-in one;
`theme/site.css` is appended to the stylesheet instead of replacing it.
Templates use `{{name}}` placeholders; read the built-in ones for the names.

`lamina.js` only enhances: previews, code highlighting and copying, table sorting, aside highlighting, the
contents marker, image zoom, math, and Mermaid. Without it every page is complete,
with TeX and diagram source left visible.
