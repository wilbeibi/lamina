"""lamina — publish a directory of Markdown as a plain static site.

    site.toml                                   name, url, categories, languages
    pages/<category>/YYYY-MM-DD-slug.md         -> public/slug.html
    pages/<category>/YYYY-MM-DD-slug.<lang>.md  -> public/slug.<lang>.html  (translation)
    pages/<category>/YYYY-MM-DD-slug/           -> public/slug/             (page assets)
    static/                                     -> public/
    theme/<file>                                overrides the built-in theme file

No front matter: category = directory, date = filename prefix, language =
filename suffix, title = the first `# ` line. Run commands in the site
directory. SKILL.md in the repository is the reference.
Set pinned = ["slug", ...] in a site.toml category to pin notes in that order.
Pinned notes show 📌 before their titles. The Atom feed stays chronological.

Math uses Temml (MathML); math and Mermaid load only where used. To self-host,
put temml.min.js, Temml-Local.css, Temml.woff2 and mermaid.min.js in theme/.
Unlinked images open in a zoom dialog. Missing local media warns at build time.
Code blocks have Copy buttons on HTTPS or localhost; h2-h4 headings have permalinks.
Tables sort complete numbers numerically and other values as text, ascending first.
Sorting ignores annotations and accepts -$2 or $-2; math previews share page macros.
"""
import argparse
import functools
import http.server
import json
import sys
import threading
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .build import build, load
from .config import THEME, WARNINGS, die, load_site
from .links import LINKS_FILE, fetch_link

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass

PORT = 8471   # off the beaten track, so it never collides with another dev server

def signature(root: Path) -> int:
    """The newest mtime among everything a build reads."""
    files = [root / 'site.toml', root / LINKS_FILE,
             *(f for d in (root / 'pages', root / 'theme', root / 'static', THEME) for f in d.rglob('*'))]
    return max((f.stat().st_mtime_ns for f in files if f.is_file()), default=0)

def cmd_serve(root: Path) -> None:
    out = build(root)
    last = signature(root)
    handler = functools.partial(QuietHandler, directory=str(out))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f'lamina: serving {out} at http://127.0.0.1:{PORT}/, rebuilding on change (Ctrl-C to stop)')
    try:
        while True:
            time.sleep(1)
            if (sig := signature(root)) != last:
                last = sig
                try:
                    build(root)
                except SystemExit:
                    pass                    # die() has already said why
                except Exception as e:
                    print(f'lamina: build failed: {e!r}', file=sys.stderr)
    except KeyboardInterrupt:
        pass

def cmd_links(root: Path) -> None:
    site = load_site(root)
    ctx = load(root, site)
    # entries for links no page has any more are dropped; a failed fetch keeps the old one.
    # Only new links are fetched: delete links.json to refetch everything.
    cache = {u: v for u, v in ctx.links.items() if u in ctx.external}
    todo = sorted(ctx.external - cache.keys())
    print(f'lamina: {len(ctx.external)} external links, fetching {len(todo)}')
    miss = []
    with ThreadPoolExecutor(8) as ex:
        for url, got in zip(todo, ex.map(fetch_link, todo), strict=True):
            if got:
                cache[url] = got
            elif url not in cache:
                miss.append(url)
    for url in miss:
        print(f'lamina: no preview for {url}', file=sys.stderr)
    (root / LINKS_FILE).write_text(json.dumps(dict(sorted(cache.items())), ensure_ascii=False, indent=1) + '\n',
                                   encoding='utf-8')
    print(f'lamina: {len(cache)} previews in {root / LINKS_FILE} ({len(miss)} unavailable)')

Command = Callable[[argparse.Namespace], object]

def main(argv: Sequence[str] | None = None) -> None:
    root = Path.cwd()
    ap = argparse.ArgumentParser(prog='lamina', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(metavar='command', title='commands (default: build)')

    def command(name: str, text: str, run: Command) -> argparse.ArgumentParser:
        sp = sub.add_parser(name, help=text, description=text)
        sp.set_defaults(run=run)
        return sp

    def strict(a: argparse.Namespace) -> None:
        build(root)
        if WARNINGS:
            die(f'{len(WARNINGS)} warnings')

    command('build', 'build into public/; exit 1 on warnings (dead links, missing media, bad anchors, unresolved [[terms]])', strict)
    command('serve', f'build, serve public/ at http://127.0.0.1:{PORT}/ and rebuild on change, until Ctrl-C', lambda a: cmd_serve(root))
    command('links', 'fetch titles and descriptions of new external links into links.json for hover previews', lambda a: cmd_links(root))
    ap.set_defaults(run=strict)
    a = ap.parse_args(argv)
    a.run(a)
