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
as `lamina: ...`; `check` exits 1 if there were any. Run commands in the
site directory.
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
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .build import build, load
from .config import HERE, THEME, WARNINGS, die, load_site
from .links import LINKS_FILE, fetch_link

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass

PORT = 8471   # off the beaten track, so it never collides with another dev server

def cmd_serve(out: Path) -> None:
    handler = functools.partial(QuietHandler, directory=str(out))
    with http.server.ThreadingHTTPServer(('127.0.0.1', PORT), handler) as srv:
        print(f'lamina: serving {out} at http://127.0.0.1:{PORT}/  (Ctrl-C to stop)')
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass

def signature(root: Path) -> int:
    """The newest mtime among everything a build reads."""
    files = [root / 'site.toml', root / LINKS_FILE,
             *(f for d in (root / 'pages', root / 'theme', root / 'static', THEME) for f in d.rglob('*'))]
    return max((f.stat().st_mtime_ns for f in files if f.is_file()), default=0)

def cmd_watch(root: Path) -> None:
    print('lamina: watching for changes (Ctrl-C to stop)')
    last: int | None = None
    try:
        while True:
            if (sig := signature(root)) != last:
                last = sig
                try:
                    build(root)
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

def cmd_new(root: Path, category: str, slug: str) -> None:
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
    f.write_text(f'# {slug}\n\n', encoding='utf-8')
    print(f)

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

    def check(a: argparse.Namespace) -> None:
        build(root)
        if WARNINGS:
            die(f'{len(WARNINGS)} warnings')
        print('lamina: check ok')

    command('init', 'write site.toml and a first page into DIR (default: here), then stop', lambda a: cmd_init(Path(a.directory))
            ).add_argument('directory', metavar='DIR', nargs='?', default='.')
    command('build', 'build the site into public/; prints a summary, warnings on stderr', lambda a: build(root))
    command('check', 'build, then exit 1 if there were warnings (dead links, bad anchors, unresolved [[terms]])', check)
    command('serve', f'build, then serve public/ at http://127.0.0.1:{PORT}/ until Ctrl-C', lambda a: cmd_serve(build(root)))
    command('watch', 'rebuild whenever pages/, static/, theme/ or site.toml change', lambda a: cmd_watch(root))
    new = command('new', 'create pages/CATEGORY/<today>-SLUG.md and print its path', lambda a: cmd_new(root, a.category, a.slug))
    new.add_argument('category', metavar='CATEGORY', help='a category dir from site.toml')
    new.add_argument('slug', metavar='SLUG', help='lowercased; non [a-z0-9.-] runs become -')
    command('links', 'fetch titles and descriptions of new external links into links.json for hover previews', lambda a: cmd_links(root))
    ap.set_defaults(run=lambda a: build(root))
    a = ap.parse_args(argv)
    a.run(a)
