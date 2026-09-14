<h1 align="center">Lamina: a just-enough static-site generator for markdown</h1>

<div align="center">

### Publish a directory of Markdown as a plain static site

<img src="assets/lamina-banner-reveal.png" alt="A small blue operator lifts the top page of a layered paper archive, revealing the preserved records beneath" width="800">

</div>

## Check it alive: [lamina-demo.pages.dev](https://lamina-demo.pages.dev/)

Publish a directory of Markdown as a plain static site. No front matter: the
filesystem carries the metadata. The output is ordinary files you can serve
anywhere. It is for notes, research reports, and small documentation sites; it
deliberately has no search, tags, comments, pagination, syntax highlighting,
plugins, or deployment.

Every command is non-interactive, prints what it wrote, sends warnings to
stderr as `lamina: ...`, and `check` exits 1 if there were any. `lamina --help`
is complete.

## Start

Needs [uv](https://docs.astral.sh/uv/) and Python 3.11+. Git is optional and
supplies created/updated dates.

```sh
uv tool install git+https://github.com/wilbeibi/lamina
lamina init ~/src/notes && cd ~/src/notes
lamina new notes my-first-page      # prints pages/notes/<today>-my-first-page.md
lamina check                        # build + fail on dead links; output/ is the site
lamina serve                        # http://127.0.0.1:8000/
```

`lamina watch` rebuilds on change. `--root DIR` and `-o DIR` work on every
command. `example/` is a complete site that uses every feature.

## Layout

```text
site.toml                                    settings (below)
pages/<category>/YYYY-MM-DD-slug.md          -> /slug.html
pages/<category>/YYYY-MM-DD-slug.<lang>.md   -> /slug.<lang>.html   translation
pages/<category>/YYYY-MM-DD-slug/            -> /slug/              page assets, copied verbatim
static/                                      -> /                   site assets
theme/<file>                                 overrides the built-in file of the same name
output/                                      the built site
```

- Category = directory, date = filename prefix, language = filename suffix.
  URLs are flat, so a slug must be unique across the site and moving a page
  between categories does not change its URL.
- Title = the first `# ` line (removed from the body). Description = the first
  paragraph. Created/updated = git history of the file.
- The first category is the landing page at `/`; other categories list at
  `/<dir>.html`. A page whose slug is `index` is served at `/` instead, and the
  first category's list moves to `/<dir>.html`.
- A filename starting with `_` is a draft and is skipped.

## site.toml

Every key, with its default. Only `[[category]]` and its `dir` are required.

```toml
name = "site"
description = ""
url = ""                 # needed for the Atom feed and absolute links
author = ""
lang = "en"              # default page language
output = "output"
glossary = ""            # slug of the page whose h2/h3 headings define [[terms]]
toc_min = 3              # a toc category needs this many h2s before it gets a TOC
footer = ""              # HTML appended to every footer: source link, license

[langs.zh]               # built in: en, zh. Add others like this.
name = "中文"
updated = "更新"
missing = "暂无{name}版"

[[category]]
dir = "notes"            # pages/notes/
title = "notes"          # default: dir
description = ""
index = "notes.html"     # the list page; default: index.html first, <dir>.html after
lang = "en"              # default: site lang
translations = []        # e.g. ["en"] for pages/notes/*.en.md
atom = false             # include in /atom.xml
toc = false              # table of contents on long pages
math = true              # $x$ and $$...$$ via MathJax
glossary = ""            # default: site glossary
```

## Markdown

GitHub-flavored: tables, fenced code, strikethrough, footnotes, task lists,
`<details>`, raw HTML. Links are checked at build time; a dead link, a bad
`#anchor`, or an unresolved `[[term]]` is a warning.

```markdown
# Title

First paragraph: the description.

## A section

[another page](other.html#A-section) · [[Term]] · [[Term|label]] · note[^1]

[^1]: Footnotes show as sidenotes on wide screens and popups elsewhere.
```

Heading ids are the heading text with spaces as `-`, CJK kept, duplicates
numbered. Encode a space in a URL as `%20`.

Features that turn on when a page uses them:

| Source | Result |
|---|---|
| pipe table | sortable, scrolls inside the column |
| ```` ```mermaid ```` | diagram rendered in the browser, source as fallback |
| `$x$`, `$$…$$` | MathJax SVG; `$5` and `$5-$10` stay prose |
| `> [!NOTE]` / `[!IMPORTANT]` / `[!WARNING]` | callout |
| `<ins datetime="2026-09-13" data-d="09-13">` | revision mark with a date badge |

Mermaid and MathJax load from pinned jsDelivr URLs. `lamina vendor` downloads
them into the site's `theme/vendor/` (gitignore it) and the build copies the
ones in use to `/vendor/`.

## Theme

System fonts, light and dark by OS setting. Put a file named `style.css`,
`lamina.js`, `favicon.svg`, `page.html`, `index.html`, `index-item.html`,
`atom.xml`, or `atom-item.xml` in `theme/` to replace the built-in one;
`theme/site.css` is appended to the stylesheet instead of replacing it.
Templates use `{{name}}` placeholders; read the built-in ones for the names.
