"""One page: found on disk, parsed, rendered to HTML, dated from git."""
import html
import re
import subprocess
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

import msgspec
from markdown_it import MarkdownIt
from markdown_it.token import Token
from markdown_it.utils import EnvType

from .config import Category, Site, die, warn
from .markdown import TAG, Heading, parser

Preview = tuple[str, str]   # (title, first paragraph) behind a hover popup

class Page(msgspec.Struct):
    src: Path
    cat: Category
    date: str
    slug: str
    lang: str
    canonical: bool
    out: str
    assets: Path
    # filled in by parse, render_body, stamps, decorate
    title: str = ''
    description: str = ''
    html: str = ''
    headings: list[Heading] = []
    notes: list[tuple[str, str]] = []            # (id, html)
    mermaid: bool = False
    math: bool = False
    pv: dict[str, Preview] = {}                  # anchor -> preview
    ids: set[str] = set()
    meta: str = ''
    atom_updated: str = ''
    pops: str = ''
    toc: str = ''
    terms: dict[str, str] | None = None          # glossary pages only

NAME_RE = re.compile(r'^(\d{4}-\d{2}-\d{2})-(.+)$')

def discover(root: Path, site: Site) -> list[Page]:
    pages: list[Page] = []
    for cat in site.category:
        d = root / 'pages' / cat.dir
        if not d.is_dir():
            warn(f'category directory missing: {d}')
            continue
        for md in sorted(d.glob('*.md')):
            if md.name.startswith('_'):
                continue                      # draft
            if not (m := NAME_RE.match(md.stem)):
                warn(f'{md}: not YYYY-MM-DD-slug.md, skipped')
                continue
            date, slug = m.groups()
            lang = cat.lang
            if '.' in slug:
                core, suf = slug.rsplit('.', 1)
                if suf in site.langs:
                    if suf == cat.lang:
                        die(f'{md}: .{suf} suffix, but {cat.dir} is already {suf}-canonical')
                    if suf not in cat.translations:
                        die(f'{md}: {cat.dir} declares no {suf} translations (site.toml)')
                    slug, lang = core, suf
            canonical = lang == cat.lang
            out = f'{slug}.html' if canonical else f'{slug}.{lang}.html'
            pages.append(Page(src=md, cat=cat, date=date, slug=slug, lang=lang,
                              canonical=canonical, out=out, assets=d / f'{date}-{slug}'))
    seen: dict[str, Page] = {}
    for p in pages:
        if p.out in seen:
            die(f'{p.src} and {seen[p.out].src} would both build {p.out}')
        seen[p.out] = p
    # a page whose slug is `index` is the landing page; the first category's
    # list moves aside to <dir>.html so navigation still reaches it.
    first = site.category[0]
    if 'index.html' in seen and first.index == 'index.html':
        first.index = f'{first.dir}.html'
    for cat in site.category:
        if cat.index in seen:
            die(f'{seen[cat.index].src} and the {cat.dir} index would both build {cat.index}')
    canon = {(p.cat.dir, p.slug) for p in pages if p.canonical}
    for p in pages:
        if not p.canonical and (p.cat.dir, p.slug) not in canon:
            warn(f'{p.src.name}: translation without a {p.cat.lang} canonical page')
    for cat in site.category:
        pinned: set[str] = set()
        for slug in cat.pinned:
            if slug in pinned:
                die(f'category {cat.dir}: duplicate pinned slug {slug!r}; remove the duplicate in site.toml')
            if (cat.dir, slug) not in canon:
                die(f'category {cat.dir}: pinned slug {slug!r} has no canonical page; fix pinned in site.toml')
            pinned.add(slug)
    return pages

FNREF = re.compile(r'<sup class="fn"[^>]*>.*?</sup>|<span class="aside">.*?</span>', re.DOTALL)

def plain(h: str) -> str:
    """Rendered HTML as text for descriptions and previews: tags, footnote refs, and asides dropped."""
    return html.unescape(TAG.sub('', FNREF.sub('', h)))

def fenced(lines: Iterable[str]) -> Iterator[tuple[str, bool]]:
    """(line, inside a code fence) for each line; the fences count as inside."""
    fence = None
    for ln in lines:
        f = FENCE.match(ln)
        if f and (fence is None or f.group(1)[0] == fence):
            fence = None if fence else f.group(1)[0]
            yield ln, True
        else:
            yield ln, fence is not None

def parse(p: Page) -> str:
    """Set the page's title from its first `# ` line; return the rest as its body."""
    lines = p.src.read_text(encoding='utf-8').split('\n')
    title, body = None, lines
    for i, (ln, code) in enumerate(fenced(lines)):
        if not code and ln.startswith('# '):
            title, body = ln[2:].strip(), lines[i + 1:]
            break
    p.title = title or p.slug
    return '\n'.join(body)

CJK = r'[⺀-鿿豈-﫿＀-￯]'

def describe(md: MarkdownIt, tokens: Sequence[Token], env: EnvType) -> str:
    """The first top-level paragraph, as plain text: the page description.
    Callouts (<aside>, see callouts()) are side remarks, not the lede."""
    inside = False
    for i, t in enumerate(tokens):
        if t.type == 'html_block' and t.content.startswith(('<aside', '</aside')):
            inside = t.content.startswith('<aside')
        elif t.type == 'paragraph_open' and t.level == 0 and not inside:
            # the paragraph's inline token alone: its text without the <p>
            s = plain(md.renderer.render([tokens[i + 1]], md.options, env))
            s = re.sub(f'(?<={CJK})\n(?={CJK})', '', s)
            return clip(re.sub(r'\s+', ' ', s).strip(), 160)
    return ''

def clip(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    cut = s[:n]
    if ' ' in cut[n // 2:]:
        cut = cut[:cut.rfind(' ')]
    return cut.rstrip(' ,;:，；：') + '…'

FENCE = re.compile(r'^\s{0,3}(`{3,}|~{3,})')
CALLOUT_START = re.compile(r'^\s{0,3}>\s*\[!(NOTE|IMPORTANT|WARNING|ASIDE)\](?:\s+(.*?))?\s*$', re.IGNORECASE)
CALLOUT_LINE = re.compile(r'^\s{0,3}> ?(.*)$')

def callouts(text: str) -> str:
    """Turn a small Obsidian-compatible callout subset into semantic HTML."""
    lines = list(fenced(text.split('\n')))
    out: list[str] = []
    i = 0
    while i < len(lines):
        ln, code = lines[i]
        start = None if code else CALLOUT_START.match(ln)
        i += 1
        if not start:
            out.append(ln)
            continue
        kind = start.group(1).lower()
        title = start.group(2) or kind.title()
        # an aside has no title; "> [!ASIDE] a few words" is the whole remark
        body = [start.group(2)] if kind == 'aside' and start.group(2) else []
        while i < len(lines) and (q := CALLOUT_LINE.match(lines[i][0])):
            body.append(q.group(1))
            i += 1
        out.extend([
            f'<aside class="callout callout-{kind}">',
            *([] if kind == 'aside' else [f'<p class="callout-title">{html.escape(title)}</p>']),
            '', *body, '', '</aside>',
        ])
    return '\n'.join(out)

def render_body(p: Page) -> None:
    text = callouts(parse(p))
    md = parser()
    env: EnvType = {}
    tokens = md.parse(text, env)
    h: str = md.renderer.render(tokens, md.options, env)
    p.description = describe(md, tokens, env)
    p.headings = env.get('headings', [])
    p.mermaid, p.math = '<pre class="mermaid">' in h, 'class="math"' in h

    # footnote bodies feed the hover popups (minus the back link)
    p.notes = [(n, re.sub(r' <a href="#fnref-[^"]*" class="fnback"[^<]*</a>', '', body))
               for n, body in re.findall(r'<li id="fn-(\d+)">(.*?)</li>', h, re.DOTALL)]

    # previews: '' -> (title, description); heading id -> (heading, first
    # paragraph). Taken before the sidenotes go in, so no note text leaks in.
    pv: dict[str, Preview] = {'': (p.title, p.description)}
    for hd in p.headings:
        pos = h.find(f'<h{hd.level} id="{html.escape(hd.id, quote=False).replace(chr(34), "&quot;")}">')
        seg = re.split(r'<h[2-4]', h[pos + 10:], maxsplit=1)[0] if pos >= 0 else ''
        m = re.search(r'<p>(.*?)</p>', re.sub(r'<aside\b.*?</aside>', '', seg, flags=re.DOTALL), re.DOTALL)
        pv[hd.id] = (hd.text, clip(plain(m.group(1)).strip(), 240) if m else '')
    if is_glossary(p.slug):
        h = define_terms(p, h, pv)

    # a sidenote after each note's first ref, shown in the margin when wide
    # (style.css). Notes with block content stay popup + endnote only.
    for n, body in p.notes:
        if re.search(r'<(pre|ul|ol|div|blockquote|table)\b', body):
            continue
        inner = re.sub(r'</p>\s*<p>', '<br>', body.strip()).removeprefix('<p>').removesuffix('</p>')
        at = h.find('</sup>', h.find(f'<sup class="fn" id="fnref-{n}">')) + 6
        h = f'{h[:at]}<span class="sn"><b>{n}</b> {inner}</span>{h[at:]}'
    p.html = h
    p.pv = pv
    p.ids = {html.unescape(i) for i in re.findall(r'\sid="([^"]*)"', h)}

# a glossary entry: a list item that opens with bold text, also inside a loose
# item's <p> or a revision <ins>. Its definition runs to the item's first break.
TERM_LI = re.compile(r'<li>(\s*(?:<p>)?\s*(?:<ins\b[^>]*>)?\s*<strong>(.*?)</strong>)', re.DOTALL)
TERM_END = re.compile(r'</li>|</p>|<[uo]l\b')
PAREN = re.compile(r'\s*[（(]([^（）()]*)[）)]')

def term_keys(term: str) -> list[str]:
    """Other names an entry answers to: the term without its parentheticals,
    each parenthetical, and each ` / ` alternative of those.
    "EPS (earnings per share)" -> EPS, earnings per share; "long / short" -> long, short."""
    names = [PAREN.sub('', term).strip(), *PAREN.findall(term)]
    return [k.strip() for n in names for k in [n, *n.split(' / ')] if k.strip()]

def is_glossary(slug: str) -> bool:
    """`glossary` or `<anything>-glossary` is its category's glossary; outputs are flat, hence the prefix."""
    return slug == 'glossary' or slug.endswith('-glossary')

def define_terms(p: Page, h: str, pv: dict[str, Preview]) -> str:
    """A glossary's [[terms]]: its h2/h3 headings, then every "- **Term**: ..."
    list item, which gets a heading-style id and a preview of its definition.
    Headings win over entry names, and entry names over term_keys aliases."""
    names: dict[str, str] = {}
    aliases: dict[str, str] = {}
    out: list[str] = []
    last = 0
    taken = {html.unescape(i) for i in re.findall(r'\sid="([^"]*)"', h)}
    for m in TERM_LI.finditer(h):
        term = plain(m.group(2)).strip()
        if not term:
            continue
        ident = base = re.sub(r'\s+', '-', term)
        n = 1
        while ident in taken:
            n += 1
            ident = f'{base}-{n}'
        taken.add(ident)
        e = TERM_END.search(h, m.end())
        d = plain(h[m.end():e.start() if e else len(h)]).strip()
        # a leading "(report links)" aside before the colon is navigation, not definition
        d = re.sub(r'^[（(][^（）()]*[）)]\s*(?=[:：])', '', d).lstrip(' :：—–')
        pv[ident] = (term, clip(d, 240))
        names.setdefault(term.lower(), ident)
        for k in term_keys(term):
            aliases.setdefault(k.lower(), ident)
        out += [h[last:m.start()], f'<li id="{html.escape(ident)}" class="term">', m.group(1)]
        last = m.end()
    heads = {hd.text.lower(): hd.id for hd in p.headings if hd.level <= 3}
    p.terms = aliases | names | heads
    return ''.join(out) + h[last:]

def git(root: Path, *args: str) -> str:
    try:
        r = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, check=False)
        return r.stdout.strip() if r.returncode == 0 else ''
    except FileNotFoundError:
        return ''

def stamps(p: Page, root: Path, site: Site) -> None:
    log = git(root, 'log', '--follow', '--diff-filter=AM', '--format=%cI', '--', str(p.src.relative_to(root))).splitlines()
    first = log[-1] if log else ''           # the commit that added the file
    last = log[0] if len(log) > 1 else ''    # the latest edit, if any
    label = site.langs[p.lang].updated
    upd = f' · {label} <time datetime="{last[:10]}">{last[:10]}</time>' if last and last[:10] != p.date else ''
    p.meta = f'<time datetime="{p.date}">{p.date}</time>{upd}'
    p.atom_updated = last or first or f'{p.date}T00:00:00Z'
