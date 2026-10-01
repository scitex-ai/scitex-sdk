"""scitex-sdk ui component-usage linter — UI-101..107.

Public surface:
- :func:`build_rules`               — rule corpus (UI-101..107 :class:`Rule`s)
- :func:`scan_path`                 — walk a directory / file and emit Issues
- :class:`UIViolation`              — a single concrete violation
- :func:`main` (via ``scitex-sdk ui lint``) — CLI entry point

Doctrine: `_skills/scitex-ui/40_component-usage-doctrine.md`.
"""

from ._rules import UIViolation, build_rules
from ._checker import scan_path

__all__ = ["build_rules", "scan_path", "UIViolation"]
