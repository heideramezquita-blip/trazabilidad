"""La URL privada solo existe en la configuración local del usuario."""
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
import re
import tomllib

ROOT = Path(__file__).resolve().parents[2]

@dataclass(frozen=True)
class Config:
    url: str = ''
    browser: str = 'msedge'
    profile_dir: Path = ROOT / '.local' / 'browser-profile'
    report_dir: Path = ROOT / '.local' / 'reports'
    control_timeout_ms: int = 15000
    automatic_timeout_ms: int = 10000
    pause_between_rows_ms: int = 0
    decimal_separator: str = 'auto'
    year_override_own: int | None = None
    third_zero_year: str = 'error'


def validate_form_url(url):
    try:
        p = urlsplit(url)
        if p.scheme != 'https' or p.username or p.password or p.port or p.fragment:
            raise ValueError()
        if p.hostname == 'script.google.com' and re.fullmatch(r'/macros/s/[A-Za-z0-9_-]+/(?:exec|dev)/?', p.path):
            return
        if p.hostname == 'script.googleusercontent.com' and p.path == '/macros/echo':
            return
    except (ValueError, AttributeError):
        pass
    raise ValueError('La URL debe ser HTTPS y corresponder a un despliegue válido de Google Apps Script.')


def load_config(filename: Path | None = None, cli_url: str | None = None):
    path = filename or ROOT / 'config.local.toml'
    data = tomllib.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    options = data.get('cargador', {})
    if cli_url:
        options['url'] = cli_url
    values = {key: v for key, v in options.items() if key in Config.__dataclass_fields__}
    for key in ('profile_dir', 'report_dir'):
        if key in values:
            loc = Path(values[key]).expanduser()
            values[key] = loc if loc.is_absolute() else ROOT / loc
    c = Config(**values)
    if c.url:
        validate_form_url(c.url)
    if c.browser not in ('msedge', 'chromium'):
        raise ValueError('browser debe ser msedge o chromium.')
    if c.decimal_separator not in ('auto', 'dot', 'comma'):
        raise ValueError('decimal_separator debe ser auto, dot o comma.')
    if c.third_zero_year not in ('error', 'empty', 'preserve'):
        raise ValueError('third_zero_year debe ser error, empty o preserve.')
    if c.year_override_own is not None and not (1000 <= c.year_override_own <= 9999):
        raise ValueError('year_override_own debe ser un año de cuatro cifras.')
    if not (1000 <= c.control_timeout_ms <= 120000 and 1000 <= c.automatic_timeout_ms <= 120000):
        raise ValueError('timeouts fuera de rango.')
    if not 0 <= c.pause_between_rows_ms <= 10000:
        raise ValueError('pausa fuera de rango.')
    return c
