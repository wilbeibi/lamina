"""site.toml as msgspec structs, and the warn/die channel every module reports through."""
import sys
import tomllib
from pathlib import Path
from typing import Any, NoReturn

import msgspec

HERE = Path(__file__).resolve().parent
THEME = HERE / 'theme'

WARNINGS: list[str] = []

def warn(msg: str) -> None:
    WARNINGS.append(msg)
    print(f'lamina: {msg}', file=sys.stderr)

def die(msg: str, code: int = 1) -> NoReturn:
    print(f'lamina: {msg}', file=sys.stderr)
    sys.exit(code)

class Lang(msgspec.Struct, forbid_unknown_fields=True):
    """UI strings for one language (site.toml [langs.<code>])."""
    name: str
    updated: str = 'updated'
    missing: str = 'no {name} version yet'
    contents: str = 'Contents'

# a [langs.xx] table completes one of these, or defines a new language
LANG_DEFAULTS: dict[str, dict[str, str]] = {
    'en': {'name': 'EN'},
    'zh': {'name': '中文', 'updated': '更新', 'missing': '暂无{name}版', 'contents': '目录'},
}

class Category(msgspec.Struct, forbid_unknown_fields=True):
    """One [[category]] table: a directory of pages with a list page."""
    dir: str
    title: str = ''                 # default: dir
    description: str = ''
    lang: str = ''                  # default: the site's
    translations: list[str] = []
    index: str = ''                 # default: index.html for the first category, else <dir>.html
    atom: bool = False
    math: bool = True
    toc: bool = False
    glossary: str | None = None     # default: the site's

class Site(msgspec.Struct, forbid_unknown_fields=True):
    """site.toml with every default filled in."""
    name: str = 'site'
    description: str = ''
    url: str = ''
    author: str = ''
    lang: str = 'en'
    publish_dir: str = 'public'
    glossary: str = ''
    toc_min: int = 3
    footer: str = ''
    langs: dict[str, Lang] = {}
    category: list[Category] = []

def load_site(root: Path) -> Site:
    p = root / 'site.toml'
    if not p.exists():
        die(f'no site config at {p}')
    raw = tomllib.loads(p.read_text(encoding='utf-8'))
    try:
        user = msgspec.convert(raw.get('langs', {}), dict[str, dict[str, Any]])
        raw['langs'] = {k: LANG_DEFAULTS.get(k, {'name': k.upper()}) | user.get(k, {}) for k in LANG_DEFAULTS | user}
        site = msgspec.convert(raw, Site)
    except msgspec.ValidationError as e:
        die(f'site.toml: {e}')
    if not site.category:
        die('site.toml needs at least one [[category]]')
    for i, cat in enumerate(site.category):
        cat.title = cat.title or cat.dir
        cat.lang = cat.lang or site.lang
        cat.index = cat.index or ('index.html' if i == 0 else f'{cat.dir}.html')
        if cat.glossary is None:
            cat.glossary = site.glossary
        for lang in [cat.lang, *cat.translations]:
            if lang not in site.langs:
                die(f'category {cat.dir}: unknown language {lang!r} (add [langs.{lang}] to site.toml)')
    return site
