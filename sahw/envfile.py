"""sahw.envfile — the optional machine-config file the server reads before it listens.

SAHW's configuration is the process environment: SAHW_PORT, SAHW_RUNS_ROOT, SAHW_SAH_TREE. Which
port the UI answers on, which folder holds this box's run logs, and where the SAH package it
launches lives are facts about one machine: useful in one place, and not the tree to ship. So they
live in a file the .gitignore excludes, while a committed example (.env.example) shows the shape.

The loader is tiny and stdlib-only on purpose. It reads KEY=VALUE lines: a blank line or a whole-line
`#` comment is skipped, an optional `export ` prefix is dropped, the line's first `=` splits the key
from the value, and one pair of matching single or double quotes around the value is removed. It does
not interpolate `$`, does not execute anything, and does not strip an inline ` # comment`, so a value
is everything after the first `=` — which keeps a Windows path or a URL with a fragment intact.

Precedence is the standard dotenv one. The file is merged with setdefault, so a variable the
environment already holds — the operator's shell, a CI, a launcher — wins over the file. The file is a
floor that fills the gaps the tree does not carry, never a ceiling over a value set on purpose. The
command line beats both, because a flag is the newest thing the operator said.
"""
from __future__ import annotations

import os


def parse_env_file(text: str) -> dict[str, str]:
    """Parse the body of a .env file into {key: value}.

    A blank line or a whole-line `#` comment is skipped. Otherwise the line's first `=` splits the key
    from the value; the key is stripped and must be a bare name (no internal whitespace) or the line is
    dropped. The value is stripped of surrounding whitespace and of one pair of matching quotes.
    """
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        if not key or " " in key or "\t" in key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        out[key] = value
    return out


def load_env_file(path: str) -> dict[str, str]:
    """Parse one .env file on disk, or {} when the path is not a readable file."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return parse_env_file(handle.read())
    except OSError:
        return {}


def repo_root() -> str:
    """The directory that holds the `sahw` package — the tree the .env and the front sit in."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def apply_env_file() -> str | None:
    """Merge the .env into the process environment for the keys it does not already set, and return the
    path it read, or None when there was no file to read.

    The path is $SAHW_ENV_FILE when set (absolute, or relative to the caller's working directory), else
    <repo_root>/.env. Only keys the environment lacks are set, so a value the operator put in the shell
    is never overridden by the file.
    """
    path = os.environ.get("SAHW_ENV_FILE") or os.path.join(repo_root(), ".env")
    values = load_env_file(path)
    if not values:
        return None
    for key, value in values.items():
        os.environ.setdefault(key, value)
    return path
