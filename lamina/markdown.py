"""The markdown-it parser: wikilinks, asides, footnotes, and math rendered to our markup."""
import functools
import html
import re
from collections.abc import Callable, Sequence
from typing import NamedTuple

from markdown_it import MarkdownIt
from markdown_it.common.utils import escapeHtml
from markdown_it.helpers import parseLinkLabel
from markdown_it.renderer import RendererHTML
from markdown_it.rules_inline import StateInline
from markdown_it.token import Token
from markdown_it.utils import EnvType, OptionsDict
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.tasklists import tasklists_plugin

TAG = re.compile(r'<[^>]+>')

class Heading(NamedTuple):
    level: int
    id: str
    text: str

def heading_open(s: RendererHTML, t: Sequence[Token], i: int, o: OptionsDict, e: EnvType) -> str:
    """h2-h4 get an id: the heading text, whitespace -> '-', deduped; env['headings'] collects them."""
    tag = t[i].tag
    if tag not in ('h2', 'h3', 'h4'):
        return s.renderToken(t, i, o, e)
    text = TAG.sub('', s.renderInline(t[i + 1].children or [], o, e))
    base = re.sub(r'\s+', '-', text.strip()) or 'section'
    used = e.setdefault('heading_ids', {})
    used[base] = n = used.get(base, 0) + 1
    ident = base if n == 1 else f'{base}-{n}'
    e.setdefault('headings', []).append(Heading(int(tag[1]), html.unescape(ident), html.unescape(text).strip()))
    return f'<{tag} id="{ident.replace(chr(34), "&quot;")}">'

def fence(s: RendererHTML, t: Sequence[Token], i: int, o: OptionsDict, e: EnvType) -> str:
    """```mermaid -> <pre class="mermaid"> (rendered client-side); any other fence as usual."""
    if t[i].info.split()[:1] != ['mermaid']:
        return s.fence(t, i, o, e)
    return f'<pre class="mermaid">{escapeHtml(t[i].content)}</pre>\n'

# [[wiki links]] render to a placeholder tag: resolving them needs every page
# parsed first, so decorate() rewrites <x-wikilink> once the site is known.
def wikilinks(md: MarkdownIt) -> None:
    """[[target]] and [[target|label]] -> <x-wikilink data-target="...">."""
    def rule(state: StateInline, silent: bool) -> bool:
        src, pos = state.src, state.pos
        if not src.startswith('[[', pos):
            return False
        end = src.find(']]', pos + 2)
        if end < 0 or set('[]') & set(src[pos + 2:end]):
            return False
        target, _, label = src[pos + 2:end].partition('|')
        if not silent:
            state.push('html_inline', '', 0).content = (
                f'<x-wikilink data-target="{html.escape(target.strip())}">{html.escape((label or target).strip(), quote=False)}</x-wikilink>')
        state.pos = end + 2
        return True

    md.inline.ruler.before('link', 'wikilink', rule)

# ^[~remark] is an author's aside: an inline footnote without the number,
# popup, or endnote. style.css keeps it in the line, or in the margin when wide.
# [these words]^[~remark] also marks the words it is about (<span class="as-t">);
# without them lamina.js takes the clause before the aside. Hovering either
# side highlights both.
def asides(md: MarkdownIt) -> None:
    def emit(state: StateInline, start: int, end: int, html_open: str) -> None:
        # parse into a fresh list: the nested parse's post-processing joins
        # text tokens, which would shift the outer paragraph's delimiter indexes
        inner: list[Token] = []
        state.md.inline.parse(state.src[start:end], state.md, state.env, inner)
        state.push('html_inline', '', 0).content = html_open
        state.tokens.extend(inner)
        state.push('html_inline', '', 0).content = '</span>'

    def rule(state: StateInline, silent: bool) -> bool:
        src, pos = state.src, state.pos
        # mid: the ']' closing the marked words, or just before a bare '^[~'
        mid = parseLinkLabel(state, pos) if src[pos] == '[' else pos - 1
        if mid < 0 or not src.startswith('^[~', mid + 1):
            return False
        end = parseLinkLabel(state, mid + 2)
        if end < 0:
            return False
        if not silent:
            if mid >= pos:
                emit(state, pos + 1, mid, '<span class="as-t">')
            emit(state, mid + 4, end, '<span class="aside">')
        state.pos = end + 1
        return True

    md.inline.ruler.before('link', 'aside', rule)

RenderRule = Callable[[RendererHTML, Sequence[Token], int, OptionsDict, EnvType], str]

def fn_id(t: Token) -> str:
    """A footnote ref's id: its note number, plus -k for the k-th ref to the same note."""
    n = str(t.meta['id'] + 1)
    return f"{n}-{t.meta['subId'] + 1}" if t.meta.get('subId') else n

def footnote_ref(s: RendererHTML, t: Sequence[Token], i: int, o: OptionsDict, e: EnvType) -> str:
    n = t[i].meta['id'] + 1
    return f'<sup class="fn" id="fnref-{fn_id(t[i])}"><a href="#fn-{n}" data-pop="pop-fn-{n}">{n}</a></sup>'

def footnote_anchor(s: RendererHTML, t: Sequence[Token], i: int, o: OptionsDict, e: EnvType) -> str:
    return f' <a href="#fnref-{fn_id(t[i])}" class="fnback" aria-label="back">↩</a>'

def tex(tag: str, o: str, c: str, tail: str = '') -> RenderRule:
    """A render rule wrapping the token's TeX in MathJax delimiters."""
    return lambda s, t, i, opts, env: f'<{tag} class="math">{o}{html.escape(t[i].content.strip())}{c}</{tag}>{tail}'

@functools.cache
def parser(math: bool) -> MarkdownIt:
    md = (MarkdownIt('commonmark', {'html': True, 'linkify': True, 'xhtmlOut': False})
          .enable(['table', 'strikethrough', 'linkify'])
          .use(tasklists_plugin).use(footnote_plugin).use(wikilinks).use(asides))
    # autolink only a real scheme. Never a bare e-mail, never a bare domain --
    # prose is full of "fly.io" and "DESIGN.md" that must stay text.
    assert md.linkify is not None
    md.linkify.set({'fuzzy_email': False, 'fuzzy_link': False})
    for name, out in {'s_open': '<del>', 's_close': '</del>', 'footnote_close': '</li>',
                      'footnote_block_open': '<section class="footnotes"><ol>',
                      'footnote_block_close': '</ol></section>\n'}.items():
        md.add_render_rule(name, lambda s, t, i, o, e, out=out: out)

    # footnotes in our markup: numbered refs with hover popups, a plain
    # <section class="footnotes"> at the end, no <hr>.
    md.add_render_rule('footnote_ref', footnote_ref)
    md.add_render_rule('footnote_open', lambda s, t, i, o, e: f'<li id="fn-{t[i].meta["id"] + 1}">')
    md.add_render_rule('footnote_anchor', footnote_anchor)
    md.add_render_rule('heading_open', heading_open)
    md.add_render_rule('fence', fence)
    # GFM tables get the same scroll/breakout wrapper hand-written ones use
    md.add_render_rule('table_open', lambda s, t, i, o, e: '<div class="t"><table>\n')
    md.add_render_rule('table_close', lambda s, t, i, o, e: '</table></div>\n')
    if math:
        # no space inside the delimiters, no digit hugging them -- keeps
        # "$5-$10" and "raised $Y @ $Z" in prose out of math
        md.use(dollarmath_plugin, double_inline=True,
               allow_space=False, allow_digits=False)

        # MathJax delimiters, emitted directly. Display blocks get their own
        # div (scrolls when wide); a labelled block stays inline in a <p> so
        # the label can follow it.
        display = tex('span', '\\[', '\\]')
        md.add_render_rule('math_inline', tex('span', '\\(', '\\)'))
        md.add_render_rule('math_inline_double', display)
        md.add_render_rule('math_block', tex('div', '\\[', '\\]', '\n'))
        md.add_render_rule('math_block_label', lambda s, t, i, o, e: f'<p>{display(s, t, i, o, e)} ({t[i].info})</p>\n')
    return md
