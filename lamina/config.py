"""site.toml as dataclasses, and the warn/die channel every module reports through."""
import sys
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any, NoReturn, TypeVar

HERE = Path(__file__).resolve().parent

THEME = HERE / 'theme'

VENDOR_LIST = HERE / 'vendor.txt'

WARNINGS: list[str] = []

def warn(msg: str) -> None:
    WARNINGS.append(msg)
    print(f'lamina: {msg}', file=sys.stderr)

def die(msg: str, code: int = 1) -> NoReturn:
    print(f'lamina: {msg}', file=sys.stderr)
    sys.exit(code)

@dataclass(slots=True)
class Lang:
    """UI strings for one language (site.toml [langs.<code>])."""
    name: str
    updated: str = 'updated'
    missing: str = 'no {name} version yet'
    contents: str = 'Contents'

LANG_DEFAULTS = {
    'en': Lang(name='EN'),
    'zh': Lang(name='中文', updated='更新', missing='暂无{name}版', contents='目录'),
}

@dataclass(slots=True)
class Category:
    """One [[category]] table: a directory of pages with a list page."""
    dir: str
    title: str
    description: str = ''
    lang: str = 'en'
    translations: list[str] = field(default_factory=list)
    index: str = 'index.html'
    atom: bool = False
    math: bool = True
    toc: bool = False
    glossary: str = ''

@dataclass(slots=True)
class Site:
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
    langs: dict[str, Lang] = field(default_factory=dict)
    category: list[Category] = field(default_factory=list)

Config = TypeVar('Config', Site, Category, Lang)

def configure(obj: Config, cfg: Mapping[str, Any], where: str) -> Config:
    """Set each key of a TOML table on its dataclass; die on a key it lacks."""
    known = {f.name for f in fields(obj)}
    for k, v in cfg.items():
        if k not in known:
            die(f'{where}: unknown key {k!r}')
        setattr(obj, k, v)
    return obj

def load_site(root: Path) -> Site:
    p = root / 'site.toml'
    if not p.exists():
        die(f'no site config at {p}')
    cfg = tomllib.loads(p.read_text(encoding='utf-8'))
    site = configure(Site(), {k: v for k, v in cfg.items() if k not in ('category', 'langs')}, 'site.toml')
    site.langs = {k: replace(v) for k, v in LANG_DEFAULTS.items()}
    for k, v in cfg.get('langs', {}).items():
        base = site.langs.get(k) or Lang(name=k.upper())
        site.langs[k] = configure(base, v, f'[langs.{k}]')
    for i, c in enumerate(cfg.get('category', [])):
        if 'dir' not in c:
            die('every [[category]] needs a dir')
        cat = Category(dir=c['dir'], title=c['dir'], lang=site.lang, glossary=site.glossary,
                       index='index.html' if i == 0 else f"{c['dir']}.html")
        configure(cat, c, f"[[category]] {c['dir']}")
        for lang in [cat.lang, *cat.translations]:
            if lang not in site.langs:
                die(f'category {cat.dir}: unknown language {lang!r} (add [langs.{lang}] to site.toml)')
        site.category.append(cat)
    if not site.category:
        die('site.toml needs at least one [[category]]')
    return site
