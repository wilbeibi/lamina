"""lamina — publish a directory of Markdown as a plain static site.

    site.toml                                   name, url, categories, languages
    pages/<category>/YYYY-MM-DD-slug.md         -> public/slug.html
    pages/<category>/YYYY-MM-DD-slug.<lang>.md  -> public/slug.<lang>.html  (translation)
    pages/<category>/YYYY-MM-DD-slug/           -> public/slug/             (page assets)
    static/                                     -> public/
    theme/<file>                                overrides the built-in theme file

No front matter. Category = directory, date = filename prefix, language =
filename suffix, title = the first `# ` line, description = the first
paragraph, created/updated = git history. A page whose slug is `index` is
served at /. A filename starting with `_` is a draft. Warnings go to stderr
as `lamina: ...`; `check` exits 1 if there were any. Every command takes
--root DIR (the site, default .) and -o/--publish-dir DIR (default ROOT/public).
"""
import argparse
import datetime
import functools
import http.server
import json
import re
import shutil
import sys
import time
import urllib.request
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .build import build, load, vendor_list
from .config import HERE, THEME, WARNINGS, die, load_site
from .links import LINKS_FILE, fetch_link

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass

def cmd_serve(out: Path, port: int) -> None:
    handler = functools.partial(QuietHandler, directory=str(out))
    with http.server.ThreadingHTTPServer(('127.0.0.1', port), handler) as srv:
        print(f'lamina: serving {out} at http://127.0.0.1:{port}/  (Ctrl-C to stop)')
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass

def signature(root: Path) -> int:
    """The newest mtime among everything a build reads."""
    files = [root / 'site.toml', root / LINKS_FILE,
             *(f for d in (root / 'pages', root / 'theme', root / 'static', THEME) for f in d.rglob('*'))]
    return max((f.stat().st_mtime_ns for f in files if f.is_file()), default=0)

def cmd_watch(root: Path, outdir: str | None) -> None:
    print('lamina: watching for changes (Ctrl-C to stop)')
    last: int | None = None
    try:
        while True:
            if (sig := signature(root)) != last:
                last = sig
                try:
                    build(root, outdir)
                except SystemExit:
                    pass                    # die() has already said why
                except Exception as e:
                    print(f'lamina: build failed: {e!r}', file=sys.stderr)
            time.sleep(1)
    except KeyboardInterrupt:
        pass

def cmd_init(root: Path) -> None:
    root = root.resolve()
    if (root / 'site.toml').exists():
        die(f'{root}/site.toml exists; refusing to overwrite an existing site')
    page = root / 'pages' / 'notes' / f'{datetime.date.today().isoformat()}-first-note.md'
    if page.exists():
        die(f'{page} exists; refusing to overwrite')
    page.parent.mkdir(parents=True, exist_ok=True)
    toml = (HERE / 'init' / 'site.toml').read_text(encoding='utf-8').replace('{name}', root.name or 'site')
    (root / 'site.toml').write_text(toml, encoding='utf-8')
    shutil.copy(HERE / 'init' / 'first-note.md', page)
    print(f'lamina: wrote {root / "site.toml"}\nlamina: wrote {page}\nlamina: edit site.toml, then build here')

def cmd_new(root: Path, category: str, slug: str, title: str | None) -> None:
    site = load_site(root)
    cats = {c.dir: c for c in site.category}
    if category not in cats:
        die(f'unknown category {category!r}; site.toml has: {", ".join(cats)}')
    if not (slug := re.sub(r'[^a-z0-9.-]+', '-', slug.lower()).strip('-')):
        die('slug has no ascii letters or digits; pass one explicitly')
    f = root / 'pages' / category / f'{datetime.date.today().isoformat()}-{slug}.md'
    if f.exists():
        die(f'{f} exists')
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(f'# {title or slug}\n\n', encoding='utf-8')
    print(f)

def cmd_vendor(root: Path) -> None:
    dest = root / 'theme' / 'vendor'
    dest.mkdir(parents=True, exist_ok=True)
    for name, url in vendor_list().items():
        print(f'lamina: {url} -> {dest / name}')
        with urllib.request.urlopen(url, timeout=60) as r, open(dest / name, 'wb') as w:
            shutil.copyfileobj(r, w)

def cmd_links(root: Path, refresh: bool) -> None:
    root = root.resolve()
    site = load_site(root)
    ctx = load(root, site)
    # entries for links no page has any more are dropped; a failed refetch keeps the old one
    cache = {u: v for u, v in ctx.links.items() if u in ctx.external}
    todo = sorted(ctx.external if refresh else ctx.external - cache.keys())
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
    ap = argparse.ArgumentParser(prog='lamina', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    # --root and -o/--publish-dir are accepted before or after the command
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--root', default=argparse.SUPPRESS, help='site directory (default: current directory)')
    common.add_argument('-o', '--publish-dir', default=argparse.SUPPRESS, help='where to write the site (default: ROOT/public)')
    ap.add_argument('--root', default='.', help=argparse.SUPPRESS)
    ap.add_argument('-o', '--publish-dir', help=argparse.SUPPRESS)
    sub = ap.add_subparsers(metavar='command', title='commands (default: build)')

    def command(name: str, text: str, run: Command) -> argparse.ArgumentParser:
        sp = sub.add_parser(name, help=text, description=text, parents=[common])
        sp.set_defaults(run=run)
        return sp

    def check(a: argparse.Namespace) -> None:
        build(a.root, a.publish_dir)
        if WARNINGS:
            die(f'{len(WARNINGS)} warnings')
        print('lamina: check ok')

    command('init', 'write site.toml and a first page into DIR, then stop', lambda a: cmd_init(Path(a.directory or a.root))
            ).add_argument('directory', metavar='DIR', nargs='?', help='site directory (default: --root)')
    command('build', 'build the site into public/; prints a summary, warnings on stderr', lambda a: build(a.root, a.publish_dir))
    command('check', 'build, then exit 1 if there were warnings (dead links, bad anchors, unresolved [[terms]])', check)
    command('serve', 'build, then serve public/ on 127.0.0.1 until Ctrl-C', lambda a: cmd_serve(build(a.root, a.publish_dir), a.port)
            ).add_argument('--port', type=int, default=8000, help='default 8000')
    command('watch', 'rebuild whenever pages/, static/, theme/ or site.toml change', lambda a: cmd_watch(a.root, a.publish_dir))
    new = command('new', 'create pages/CATEGORY/<today>-SLUG.md and print its path', lambda a: cmd_new(a.root, a.category, a.slug, a.title))
    new.add_argument('category', metavar='CATEGORY', help='a category dir from site.toml')
    new.add_argument('slug', metavar='SLUG', help='lowercased; non [a-z0-9.-] runs become -')
    new.add_argument('--title', metavar='TEXT', help='the # heading (default: SLUG)')
    command('vendor', 'download mermaid and MathJax into theme/vendor/ so pages need no CDN', lambda a: cmd_vendor(a.root))
    command('links', 'fetch titles and descriptions of external links into links.json for hover previews', lambda a: cmd_links(a.root, a.refresh)
            ).add_argument('--refresh', action='store_true', help='refetch every link, not just new ones')
    ap.set_defaults(run=lambda a: build(a.root, a.publish_dir))
    a = ap.parse_args(argv)
    a.root = Path(a.root)
    a.run(a)
