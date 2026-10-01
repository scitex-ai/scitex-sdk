#!/usr/bin/env python3
# Timestamp: 2026-03-13
# File: scitex_sdk/app/__init__.py

"""scitex-sdk app — Write-once interface for local + cloud SciTeX apps.

Owned by scitex-sdk. Django and chat capabilities load on demand.
The same contract serves standalone and hosted leaf applications.

Public API (3 functions)::

    from scitex_sdk.app.sdk import get_files, register_backend, FilesBackend

    # Get a file backend (auto-detects local vs cloud)
    files = get_files("./project")

    # Read/write files
    content = files.read("data/config.yaml")
    files.write("output/result.csv", csv_text)

    # Register a custom backend
    register_backend("s3", my_s3_factory)
"""

from __future__ import annotations

from scitex_sdk import __version__

from ._files_api import (
    copy_file,
    delete_file,
    file_exists,
    list_files,
    read_file,
    rename_file,
    scaffold,
    validate,
    write_file,
)
from ._standalone import hosts_to_allow
from .sdk import FilesBackend, build_tree, get_files, register_backend


__all__ = [
    "__version__",
    "FilesBackend",
    "get_files",
    "register_backend",
    "build_tree",
    # What a --host bind implies for Django's ALLOWED_HOSTS. Public because
    # three repos were about to import it from a private module.
    "hosts_to_allow",
    # Flat file-ops API (mirrors the MCP tool surface so the
    # API/MCP parity stays balanced — see _files_api.py).
    "read_file",
    "write_file",
    "list_files",
    "file_exists",
    "delete_file",
    "copy_file",
    "rename_file",
    "scaffold",
    "validate",
    "chat",
    "embed",
    "paths",
    # `validator` is the legacy submodule re-export (still kept for
    # back-compat); the function `validate` above is the flat-API
    # alias for `appmaker.validate`. Different names → both coexist.
    "validator",
    "i18n",
    "plugins",
    "project_context",
]


_LOADING = set()


def __getattr__(name: str):
    """Lazy imports for optional modules (chat, paths, etc.)."""
    if name in _LOADING:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    _LOADING.add(name)
    try:
        if name in {"i18n", "plugins", "project_context"}:
            from importlib import import_module

            value = import_module(f"{__name__}.{name}")
            globals()[name] = value
            return value
        if name == "chat":
            from . import _chat

            return _chat
        if name == "embed":
            from . import embed as _embed

            return _embed
        if name == "paths":
            from . import paths as _paths

            return _paths
        if name == "validator":
            from . import validator as _validator

            return _validator
    finally:
        _LOADING.discard(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# EOF
