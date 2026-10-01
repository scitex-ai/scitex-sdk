"""Shared App contract and UI implementation for standalone and hosted apps."""

from __future__ import annotations

import importlib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

try:
    __version__ = version("scitex-sdk")
except PackageNotFoundError:
    import re

    _project = Path(__file__).parents[2] / "pyproject.toml"
    _match = re.search(r'^version\s*=\s*"([^"]+)"', _project.read_text(), re.M) if _project.exists() else None
    __version__ = _match.group(1) if _match else "0.0.0+local"


def get_frontend_package_dir() -> Path:
    """Return the packaged @scitex/sdk directory for npm/Vite resolution.

    Its export paths work in a source checkout and an installed wheel.
    """
    return Path(__file__).resolve().parent


def __getattr__(name: str):
    if name in {"app", "ui", "project"}:
        module = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["__version__", "app", "ui", "get_frontend_package_dir"]
