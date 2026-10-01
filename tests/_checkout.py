"""Locate SDK UI SOURCE for source-specific asset guards.

Installed artifact closure is checked separately; this helper never silently
switches a source guard to a different installed package.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def package_dir() -> Path:
    path = REPO_ROOT / "src/scitex_sdk/ui"
    if not path.is_dir():
        raise RuntimeError(f"SDK UI source tree missing: {path}")
    return path


def static_dir() -> Path:
    return package_dir() / "static/scitex_sdk/ui"


def css_dir() -> Path:
    return static_dir() / "css"


def templates_dir() -> Path:
    return package_dir() / "templates"
