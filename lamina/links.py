"""links.json: cached titles and descriptions of the pages outside links point to."""
import html
import html.parser
import json
import re
import urllib.request
from pathlib import Path

from .pages import clip

# `lamina links` fetches each external link's page title and description into
# links.json at the site root (commit it). The build only reads that file, so
# it stays offline; a link with no entry gets no popup.

LINKS_FILE = 'links.json'

LinkMeta = dict[str, str]   # {'title': ..., 'description': ...}

def read_links(root: Path) -> dict[str, LinkMeta]:
    f = root / LINKS_FILE
    if not f.exists():
        return {}
    links: dict[str, LinkMeta] = json.loads(f.read_text(encoding='utf-8'))
    return links

class HeadMeta(html.parser.HTMLParser):
    """<title> and <meta name|property=... content=...> from a page's <head>."""
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.title = ''
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == 'meta' and (content := a.get('content')):
            self.meta.setdefault((a.get('property') or a.get('name') or '').lower(), content)
        elif tag == 'title':
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title += data

def fetch_link(url: str) -> LinkMeta | None:
    """{title, description} of an HTML page, or None if it can't be had."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; lamina link previews)',
        'Accept': 'text/html,application/xhtml+xml'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            if 'html' not in r.headers.get_content_type():
                return None
            text = r.read(512 * 1024).decode(r.headers.get_content_charset() or 'utf-8', errors='replace')
    except Exception:
        return None
    hm = HeadMeta()
    hm.feed(re.split(r'</head>|<body\b', text, maxsplit=1, flags=re.IGNORECASE)[0])
    m = hm.meta

    def tidy(s: str | None) -> str:
        return re.sub(r'\s+', ' ', html.unescape(s or '')).strip()
    title = tidy(m.get('og:title') or m.get('twitter:title') or hm.title)
    desc = tidy(m.get('og:description') or m.get('twitter:description') or m.get('description'))
    return {'title': clip(title, 120), 'description': clip(desc, 240)} if title or desc else None
