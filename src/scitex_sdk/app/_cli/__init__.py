#!/usr/bin/env python3
# Timestamp: 2026-03-13
# File: scitex_sdk/app/_cli/__init__.py

"""scitex-sdk app CLI — Command-line interface for scitex-app."""

from ._main import main

__all__ = ["main"]


# audit §4 — inject version into root --help
try:
    from importlib.metadata import version as _v
    main.help = (
        f"scitex-sdk app (v{_v('scitex-sdk')}) — "
        + (main.help or "").lstrip()
    )
except Exception:
    pass

# audit-cli §1a — packages with _skills/ MUST expose
# `<cli> skills {list,get,install}`. Canonical home is `dev skills` (§13);
# top level stays as a Phase W warn-forward alias.
from ._dev_group import install_dev_aliases, register_dev_group
from ._skills import skills_group as _skills_group

_dev = register_dev_group(main, _skills_group)
install_dev_aliases(main, _skills_group)
