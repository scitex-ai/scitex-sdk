#!/usr/bin/env python3
"""scitex-sdk ui — Shared frontend UI components for the SciTeX ecosystem.

Components ship as TypeScript + CSS static assets, discoverable by Django's
AppDirectoriesFinder when added to INSTALLED_APPS.

Python API provides component metadata and registration.
"""

from __future__ import annotations

from scitex_sdk import __version__

from pathlib import Path as _Path

from ._registry import get_component, list_components
from ._registry import register_component as _register_component
from . import _components  # noqa: F401 — triggers registration

# Advanced: re-export for custom component authors
register_component = _register_component


def get_static_dir() -> _Path:
    """Return the absolute path to scitex_sdk.ui's static asset directory.

    This is the directory containing ``css/`` and ``ts/`` subdirectories.
    Works for both pip-installed packages and editable (dev) installs.

    Useful for build tools (Vite, Webpack) that need to resolve
    scitex-sdk ui source files at build time.

    Returns
    -------
    pathlib.Path
        e.g. ``/usr/lib/python3.11/.../scitex_sdk/ui/static/scitex_sdk/ui``
    """
    return _Path(__file__).parent / "static" / "scitex_sdk" / "ui"


def get_docs_path() -> _Path:
    """Return the SDK's current source Markdown guidance directory."""
    return _Path(__file__).parent.parent / "_docs"


__all__ = [
    "__version__", "get_component", "list_components", "register_component",
    "get_static_dir", "get_docs_path", "branding", "mount", "project_scope",
    "mount_context", "mount_prefix",
]


def __getattr__(name: str):
    """Preserve SDK integration APIs through owned modules loaded on demand."""
    from importlib import import_module

    if name in {"branding", "mount", "project_scope"}:
        value = import_module(f"{__name__}.{name}")
    elif name in {"mount_context", "mount_prefix"}:
        value = getattr(import_module(f"{__name__}.mount"), name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    globals()[name] = value
    return value

# EOF
