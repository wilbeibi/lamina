"""The whole site: cross-page links and popups, templates, and writing public/."""
import html
import re
import shutil
import urllib.parse
from collections.abc import Iterable, Mapping
from pathlib import Path

from .config import THEME, WARNINGS, Category, Site, die, load_site, warn
from .links import read_links
from .pages import Page, discover, render_body, stamps

# pinned on purpose: a page that uses math or mermaid loads these from the CDN
MATHJAX_URL = 'https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-svg.js'
MERMAID_URL = 'https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/mermaid.min.js'

class Ctx:
    """Everything decorate() and the templates need to know about the whole site."""
    def __init__(self, root: Path, site: Site, pages: list[Page]) -> None:
        self.root = root
        self.site = site
        self.pages = pages
        self.by_out = {p.out: p for p in pages}
        self.indexes = {c.index for c in site.category}
        self.by_slug: dict[str, dict[str, Page]] = {}    # slug -> {lang: page}; outputs are flat, so slugs are unique
        for p in pages:
            self.by_slug.setdefault(p.slug, {})[p.lang] = p
        self.feed = any(c.atom for c in site.category) and bool(site.url)
        self.links = read_links(root)                     # external url -> {title, description}; `lamina links`
        self.external: set[str] = set()                   # external urls the pages link to

    def find_page(self, slug: str, lang: str) -> Page | None:
        """The page with this slug in this language, else any language, else None."""
        versions = self.by_slug.get(slug)
        if not versions:
            return None
        return versions.get(lang) or next(iter(versions.values()))

    def glossary_for(self, page: Page) -> Page | None:
        """The glossary page whose .terms (see define_terms) resolve [[terms]] here, if any."""
        if not page.cat.glossary:
            return None
        return self.find_page(page.cat.glossary, page.lang)

LINK_RE = re.compile(r'<a\b([^>]*?)\shref="([^"]*)"([^>]*)>')
TITLE_RE = re.compile(r'\stitle="([^"]*)"')
WL_RE = re.compile(r'<x-wikilink data-target="([^"]*)">(.*?)</x-wikilink>', re.DOTALL)
INTERNAL_RE = re.compile(r'^/?([^/#?]+\.html)?(?:#(.*))?$')

def dead_asset(ctx: Ctx, href: str) -> bool:
    """A local href into a page's asset directory (slug/...) that no source file backs."""
    u = urllib.parse.urlsplit(html.unescape(href))
    parts = [x for x in urllib.parse.unquote(u.path).lstrip('/').split('/') if x not in ('', '.')]
    if u.scheme or u.netloc or len(parts) < 2 or '..' in parts:
        return False
    owners = [p for p in ctx.pages if p.slug == parts[0]]
    return bool(owners) and not any(p.assets.joinpath(*parts[1:]).exists() for p in owners)

def decorate(p: Page, ctx: Ctx) -> None:
    """Resolve the page's wikilinks, check its links, attach popups and the TOC."""
    pops: dict[str, str] = {}                  # template id -> popup html
    keys: dict[tuple[str, str], str] = {}      # popup target -> template id

    def pop(key: tuple[str, str], ctxline: str, head: str, body: str) -> str:
        """The id of one <template> per target: where it is, its title, its text."""
        if key not in keys:
            keys[key] = pid = f'pop-{len(pops) + 1}'
            pops[pid] = ''.join(f'<p{cls}>{html.escape(s)}</p>' for cls, s in
                                ((' class="pop-c"', ctxline), (' class="pop-t"', head), ('', body)) if s)
        return keys[key]

    def popfor(tp: Page, anchor: str) -> str | None:
        pv = tp.pv.get(anchor)
        if pv is None or (tp is p and anchor == ''):
            return None
        return pop((tp.out, anchor), '' if anchor == '' or tp is p else tp.title, *pv)

    def wl(m: re.Match[str]) -> str:
        target, label = html.unescape(m.group(1)), m.group(2)
        pg, _, anchor = target.partition('#')
        tp = p if pg == '' else ctx.find_page(pg, p.lang)
        if tp is None and not anchor:
            g = ctx.glossary_for(p)
            if g and g.terms and target.lower() in g.terms:
                tp, anchor = g, g.terms[target.lower()]
        if tp is None or (anchor and anchor not in tp.pv):
            warn(f'{p.src.name}: unresolved wikilink [[{target}]]')
            return f'<span class="wl-missing">{label}</span>'
        href = ('' if tp is p else tp.out) + (f'#{urllib.parse.quote(anchor)}' if anchor else '')
        pid = popfor(tp, anchor)
        pop_attr = f' data-pop="{pid}"' if pid else ''
        return f'<a href="{href}" class="wl"{pop_attr}>{label}</a>'
    h = WL_RE.sub(wl, p.html)

    def external(url: str, note: str) -> str | None:
        """An outside link's popup: its site, then the title and description
        `lamina links` cached, with a link title ("...") as the description."""
        key = urllib.parse.urldefrag(url).url
        ctx.external.add(key)
        got = ctx.links.get(key, {})
        title, body = got.get('title', ''), note or got.get('description', '')
        if not (title or body):
            return None
        return pop((key, note), urllib.parse.urlsplit(key).netloc.removeprefix('www.'), title, body)

    def lk(m: re.Match[str]) -> str:
        a1, href, a3 = m.groups()
        if 'data-pop' in a1 + a3:
            return m.group(0)
        url = html.unescape(href)

        def with_pop(pid: str | None) -> str:
            return f'<a{a1} href="{href}"{a3} data-pop="{pid}">' if pid else m.group(0)
        if url.startswith(('http://', 'https://')):
            t = TITLE_RE.search(a1 + a3)
            return with_pop(external(url, html.unescape(t.group(1)) if t else ''))
        im = INTERNAL_RE.match(urllib.parse.unquote(html.unescape(href)))
        if not im:
            if dead_asset(ctx, href):
                warn(f'{p.src.name}: dead asset link {href}')
            return m.group(0)
        file, anchor = im.group(1), im.group(2) or ''
        tp = p if not file else ctx.by_out.get(file)
        if tp is None:
            if file not in ctx.indexes and not (ctx.root / 'static' / file).exists():
                warn(f'{p.src.name}: dead link {href}')
            return m.group(0)
        if anchor and anchor not in tp.pv and anchor not in tp.ids:
            warn(f'{p.src.name}: dead anchor {href}')
            return m.group(0)
        return with_pop(popfor(tp, anchor))
    h = LINK_RE.sub(lk, h)

    for ident, body in p.notes:
        pops[f'pop-fn-{ident}'] = body
    p.html = h
    p.pops = ('<div hidden>' + ''.join(f'<template id="{k}">{v}</template>' for k, v in pops.items()) + '</div>') if pops else ''

    p.toc = ''
    if p.cat.toc and sum(hd.level == 2 for hd in p.headings) >= ctx.site.toc_min:
        items = ''.join(f'<li class="toc-h{hd.level}"><a href="#{urllib.parse.quote(hd.id)}">{html.escape(hd.text)}</a></li>'
                        for hd in p.headings if hd.level in (2, 3))
        label = html.escape(ctx.site.langs[p.lang].contents)
        p.toc = (f'<nav class="toc" aria-label="{label}"><p class="toc-title">{label}</p>'
                 f'<ol>{items}</ol></nav>')

def theme_file(root: Path, name: str) -> Path | None:
    """The site's theme/<name> if it has one, else the built-in file, else None."""
    for base in (root / 'theme', THEME):
        if (base / name).exists():
            return base / name
    return None

def tpl(ctx: Ctx, name: str) -> str:
    f = theme_file(ctx.root, name)
    if f is None:
        die(f'template missing: {name}')
    return f.read_text(encoding='utf-8')

def render(t: str, values: Mapping[str, object]) -> str:
    return re.sub(r'\{\{(\w+)\}\}', lambda m: str(values.get(m.group(1), '')), t)

SEP = '<span class="sep">·</span>'

def href_of(cat: Category) -> str:
    return '/' if cat.index == 'index.html' else f'/{cat.index}'

def newest(pages: Iterable[Page]) -> list[Page]:
    return sorted(pages, key=lambda p: (p.date, p.src.name), reverse=True)

MATHJAX_CFG = ("<script>window.MathJax={tex:{inlineMath:[['\\\\(','\\\\)']],displayMath:[['\\\\[','\\\\]']],"
               "processEscapes:false},svg:{fontCache:'global'},options:{skipHtmlTags:"
               "['script','noscript','style','textarea','pre','code']}};</script>")

def langnav(p: Page, ctx: Ctx) -> tuple[str, str]:
    """The page's category and language switcher, and its hreflang <link>s."""
    cat, L = p.cat, ctx.site.langs
    parts = []
    if cat.index != 'index.html':
        parts.append(f'<a href="{href_of(cat)}">{html.escape(cat.title)}</a>')
    langs = [cat.lang, *cat.translations]
    alt = ''
    if len(langs) > 1:
        versions = ctx.by_slug[p.slug]
        for lang in langs:
            name = L[lang].name
            if lang == p.lang:
                parts.append(f'<strong>{name}</strong>')
            elif lang in versions:
                parts.append(f'<a href="{versions[lang].out}" hreflang="{lang}">{name}</a>')
            else:
                miss = L[p.lang].missing.format(name=name)
                parts.append(f'<span class="off" title="{html.escape(miss, quote=True)}">{name}</span>')
        if len(versions) > 1 and cat.lang in versions:
            alt = ''.join(f'<link rel="alternate" hreflang="{lang}" href="/{versions[lang].out}">' for lang in langs if lang in versions)
            alt += f'<link rel="alternate" hreflang="x-default" href="/{versions[cat.lang].out}">'
    nav = f'<span class="langnav">{SEP.join(parts)}</span>' if parts else ''
    return nav, alt

def feed_link(ctx: Ctx) -> str:
    return (f'<link rel="alternate" type="application/atom+xml" title="{html.escape(ctx.site.name)}" href="/atom.xml">'
            if ctx.feed else '')

def page_html(p: Page, ctx: Ctx) -> str:
    site = ctx.site
    nav, alt = langnav(p, ctx)
    head = [alt, feed_link(ctx),
            MATHJAX_CFG + f'\n<script defer src="{MATHJAX_URL}"></script>' if p.math else '',
            f'<script defer src="{MERMAID_URL}"></script>' if p.mermaid else '',
            '<script defer src="/lamina.js"></script>']
    footer = [f'<a href="{href_of(p.cat)}">← {html.escape(p.cat.title)}</a>',
              '<a href="/atom.xml">atom</a>' if ctx.feed else '', site.footer]
    return render(tpl(ctx, 'page.html'), {
        'lang': p.lang, 'site_name': html.escape(site.name), 'title': html.escape(p.title),
        'description': html.escape(p.description, quote=True), 'head': '\n'.join(x for x in head if x),
        'nav': nav, 'meta': p.meta, 'toc': p.toc, 'content': p.html, 'pops': p.pops,
        'footer': ' · '.join(x for x in footer if x),
    })

def index_html(cat: Category, ctx: Ctx) -> str:
    site = ctx.site
    items = newest(p for p in ctx.pages if p.cat is cat and p.canonical)
    item_t = tpl(ctx, 'index-item.html')
    lis = ''.join(render(item_t, {'date': p.date, 'href': p.out, 'title': html.escape(p.title),
                                  'description': html.escape(p.description, quote=True)}) for p in items)
    sec = [f'<strong>{html.escape(c.title)}</strong>' if c is cat else f'<a href="{href_of(c)}">{html.escape(c.title)}</a>'
           for c in site.category]
    secnav = f'<span class="secnav">{SEP.join(sec)}</span>' if len(sec) > 1 else ''
    first = site.category[0]
    at_root = cat.index == 'index.html'
    if at_root:
        footer = '<a href="/atom.xml">atom</a>' if ctx.feed else ''
    else:
        back, label = ('/', site.name) if cat is first else (href_of(first), first.title)
        footer = f'<a href="{back}">← {html.escape(label)}</a>'
    footer = ' · '.join(x for x in (footer, site.footer) if x)
    title = html.escape(site.name) if cat is first else f'{html.escape(cat.title)} — {html.escape(site.name)}'
    desc = cat.description or (site.description if cat is first else '')
    return render(tpl(ctx, 'index.html'), {
        'lang': cat.lang, 'site_name': html.escape(site.name), 'title': title,
        'description': html.escape(desc, quote=True), 'head': feed_link(ctx),
        'secnav': secnav, 'items': lis, 'footer': footer,
        'brand': f'<strong>{html.escape(site.name)}</strong>' if at_root else f'<a href="/">{html.escape(site.name)}</a>',
    })

def atom_xml(ctx: Ctx) -> str:
    site = ctx.site
    entries = newest(p for p in ctx.pages if p.cat.atom and p.canonical)
    url = site.url.rstrip('/')
    item_t = tpl(ctx, 'atom-item.xml')
    items = ''.join(render(item_t, {
        'title': html.escape(p.title), 'updated': p.atom_updated,
        'url': f'{url}/' if p.out == 'index.html' else f'{url}/{p.out}',
        'summary': html.escape(p.description)}) for p in entries)
    updated = max((p.atom_updated for p in entries), default='1970-01-01T00:00:00Z')
    return render(tpl(ctx, 'atom.xml'), {
        'site_name': html.escape(site.name), 'description': html.escape(site.description),
        'url': url, 'author': html.escape(site.author), 'updated': updated, 'items': items,
    })

def safe_outdir(root: Path, out: Path) -> Path:
    out = out.resolve()
    if out == root.resolve() or root.resolve().is_relative_to(out):
        die(f'refusing to use {out} as output: it contains the site')
    if (out / 'site.toml').exists() or (out / 'pages').is_dir():
        die(f'refusing to wipe {out}: it looks like a site, not a build')
    return out

def load(root: Path, site: Site) -> Ctx:
    """Discover, parse, and decorate every page: everything but the writing."""
    pages = discover(root, site)
    ctx = Ctx(root, site, pages)
    glossaries = {c.glossary for c in site.category}
    for p in pages:
        render_body(p, p.slug in glossaries)
        stamps(p, root, site)
    for p in pages:
        decorate(p, ctx)
    return ctx

def build(root: Path) -> Path:
    WARNINGS.clear()
    root = root.resolve()
    site = load_site(root)
    out = safe_outdir(root, root / site.publish_dir)
    ctx = load(root, site)
    pages = ctx.pages
    if any(c.atom for c in site.category) and not site.url:
        warn('atom feed needs `url` in site.toml; feed skipped')

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for p in pages:
        (out / p.out).write_text(page_html(p, ctx), encoding='utf-8')
        if p.assets.is_dir():
            shutil.copytree(p.assets, out / p.slug, dirs_exist_ok=True)
    for cat in site.category:
        (out / cat.index).write_text(index_html(cat, ctx), encoding='utf-8')
    if ctx.feed:
        (out / 'atom.xml').write_text(atom_xml(ctx), encoding='utf-8')

    css = tpl(ctx, 'style.css')
    extra = root / 'theme' / 'site.css'
    if extra.exists():
        css += '\n/* site.css */\n' + extra.read_text(encoding='utf-8')
    (out / 'style.css').write_text(css, encoding='utf-8')
    for name in ('lamina.js', 'favicon.svg'):
        if f := theme_file(root, name):
            shutil.copy(f, out / name)
    static = root / 'static'
    if static.is_dir():
        for f in static.rglob('*.html'):
            if f.relative_to(static).as_posix() in ctx.by_out or f.name in ctx.indexes:
                warn(f'static/{f.relative_to(static)} shadows a generated page')
        shutil.copytree(static, out, dirs_exist_ok=True)
    print(f'lamina: built {len(pages)} pages + {len(site.category)} indexes -> {out}'
          + (f' ({len(WARNINGS)} warnings)' if WARNINGS else ''))
    return out
