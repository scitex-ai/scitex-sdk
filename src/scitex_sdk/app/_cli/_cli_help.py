#!/usr/bin/env python3
"""Lazy CliHelp surface for the self-contained app CLI.

Same contract as ``scitex_sdk.ui._cli_help`` (see that module for the long
version): §4b wants help built via ``CliHelp``; PS-213 forbids optional
``scitex-dev`` imports at module scope; PS-233 wants the single guarded
import site. All three hold here — structured help where scitex-dev is
installed, plain click docstrings otherwise.
"""

from __future__ import annotations

import importlib.util
from typing import Any

__all__ = ["cli_help", "examples", "spec_command", "spec_group"]


def _present() -> bool:
    return importlib.util.find_spec("scitex_dev") is not None


def _surface(name: str) -> Any:
    if not _present():
        return None
    try:
        import scitex_dev.ecosystem as ecosystem
    except ImportError:
        return None
    return getattr(ecosystem, name, None)


def cli_help(**kwargs: Any) -> Any:
    CliHelp = _surface("CliHelp")
    if CliHelp is None:
        return None
    return CliHelp(**kwargs)


def examples(*pairs: tuple[str, str]) -> tuple[Any, ...]:
    Example = _surface("Example")
    if Example is None:
        return ()
    return tuple(Example(cmd=c, note=n) for c, n in pairs)


def spec_command(spec: Any) -> dict[str, Any]:
    SpecCommand = _surface("SpecCommand")
    if spec is None or SpecCommand is None:
        return {}
    return {"cls": SpecCommand, "help_spec": spec}


def spec_group(spec: Any) -> dict[str, Any]:
    SpecGroup = _surface("SpecGroup")
    if spec is None or SpecGroup is None:
        return {}
    return {"cls": SpecGroup, "help_spec": spec}
