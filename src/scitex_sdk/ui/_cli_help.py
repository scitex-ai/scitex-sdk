#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Resolve scitex-dev's CliHelp surface WITHOUT importing it at module scope.

Two ecosystem rules pull in opposite directions here, and this module is the
only place that reconciles them:

  §4b   a command's help must be constructed via ``CliHelp`` rather than left
        as a free-form docstring. The audit checks one thing — whether the
        command object carries a non-None ``_help_spec``.

  PS-213  console-script-deps-must-be-core. ``scitex_sdk.ui._cli:main`` is the
        entry point for the ``scitex-ui`` script, so anything it imports at
        module scope must be a CORE dependency. ``scitex-dev`` is NOT: it is
        the optional ``[cli]`` extra.

Importing ``SpecCommand`` at the top of ``_cli.py`` would satisfy §4b and break
PS-213 — a bare ``pip install scitex-sdk[all]`` followed by ``scitex-sdk ui --help`` would
raise ModuleNotFoundError. So the classes are resolved LAZILY, at decoration
time, and fall back to plain click when scitex-dev is absent.

Both rules end up honoured rather than exempted:

  * PS-213 holds because no optional dependency is imported unguarded.
  * §4b holds WHERE IT RUNS. The audit only executes in environments that have
    scitex-dev installed, and in exactly those environments the real
    ``SpecCommand`` is used and ``_help_spec`` is set.

THE FALLBACK IS NOT A SILENT FAILURE. Without the extra the help still renders,
via click's ordinary docstring path — it is simply unstructured. That is the
documented behaviour of an optional extra, not a degraded mode pretending to be
the real one. `help_available()` reports which path is live so a caller (or a
test) can tell the two apart rather than guessing.

The same shape already exists in this package: ``_linter/_rules.py`` resolves
scitex-dev's ``Rule`` this way after a module-scope import of it silently
deactivated the entire UI rule corpus (#141). This is that lesson applied
before the fact rather than after.

PS-233 — RUNTIME-IMPORT GUARD, ONE SITE
---------------------------------------
``_ecosystem_surface()`` below is the only place this module imports
scitex-dev, and that import sits inside ``try/except ImportError``. That guard
is not decoration, and it is the reason scitex-dev stays an optional ``[cli]``
extra instead of moving into ``[project.dependencies]``:

  * The rule reads IMPORT SITES. The ``find_spec`` pre-check answers "is
    scitex-dev installed"; it does not answer "can this name be imported right
    now", which is a different question — a partial or mid-upgrade install
    passes the first and fails the second — and a branch before an import is
    not a guard around it to a static scan.
  * Degradation is DEFINED and identical to the absent path: None / () / {},
    which is click's docstring help, this module's documented behaviour
    without the extra.
  * It is not a silent ``pass``. The capability's absence is the contract of
    an optional extra, and ``help_available()`` is the caller-visible signal
    for which world is live.
"""

from __future__ import annotations

import importlib.util
from typing import Any

__all__ = [
    "cli_help",
    "examples",
    "help_available",
    "spec_command",
    "spec_group",
]


def _scitex_dev_present() -> bool:
    """True when scitex-dev can be imported, without importing it."""
    return importlib.util.find_spec("scitex_dev") is not None


def help_available() -> bool:
    """Whether the structured-help path is live in THIS environment.

    Exposed so callers and tests can distinguish "structured help" from
    "click's docstring fallback" explicitly. A test that cannot tell them
    apart would pass identically in both, which is the vacuous-assertion
    shape this package has been eliminating elsewhere.
    """
    return _scitex_dev_present()


def _ecosystem_surface(name: str) -> Any:
    """Return ``scitex_dev.ecosystem.<name>``, or None when unavailable.

    THE ONE GUARD THIS MODULE NEEDS (see the module docstring). Every
    function below reaches scitex-dev's ecosystem surface through here, so the
    optional-extra contract is expressed at exactly one import site — guarded
    with ``try/except ImportError`` as PS-233 requires — rather than repeated
    at four call sites.

    Returns None when scitex-dev is absent, when importing it fails, or when
    the name is missing from an older scitex-dev. All three are the same
    defined degradation: the caller registers a plain click command/group with
    no structured spec, exactly as it does without the extra. ``getattr`` with
    a default is what keeps a version skew in that bucket instead of raising
    an AttributeError from inside a decorator during import.
    """
    if not _scitex_dev_present():
        return None
    try:
        import scitex_dev.ecosystem as ecosystem
    except ImportError:
        return None
    return getattr(ecosystem, name, None)


def cli_help(**kwargs: Any) -> Any:
    """Build a ``CliHelp``, or return None when scitex-dev is absent.

    None is the correct fallback rather than a stub: ``SpecCommand`` requires a
    real spec, and when it is unavailable we are not using ``SpecCommand`` at
    all — click takes the docstring instead.
    """
    CliHelp = _ecosystem_surface("CliHelp")
    if CliHelp is None:
        return None
    return CliHelp(**kwargs)


def examples(*pairs: tuple[str, str]) -> tuple[Any, ...]:
    """Build ``Example`` objects from ``(cmd, note)`` pairs, lazily.

    ``Example`` is scitex-dev's too, so it gets the same treatment as the rest
    of the surface. Returns an empty tuple when the extra is absent, which is
    what ``CliHelp(examples=...)`` would receive by default anyway — and the
    spec is not built at all in that case.
    """
    Example = _ecosystem_surface("Example")
    if Example is None:
        return ()
    return tuple(Example(cmd=c, note=n) for c, n in pairs)


def spec_command(spec: Any) -> dict[str, Any]:
    """Decorator kwargs registering ``spec`` as a command's help.

    Returns ``{}`` when scitex-dev is absent, so the call site reads
    ``@group.command("x", **spec_command(SPEC))`` in both worlds and needs no
    conditional of its own.
    """
    SpecCommand = _ecosystem_surface("SpecCommand")
    if spec is None or SpecCommand is None:
        return {}
    return {"cls": SpecCommand, "help_spec": spec}


def spec_group(spec: Any, **extra: Any) -> dict[str, Any]:
    """Decorator kwargs for a group; ``extra`` carries command_categories."""
    SpecGroup = _ecosystem_surface("SpecGroup")
    if spec is None or SpecGroup is None:
        return {}
    return {"cls": SpecGroup, "help_spec": spec, **extra}
