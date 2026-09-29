"""scitex-sdk project selector — re-export of the scitex-dev primitive.

The selection state lives in scitex-dev (CUI-level, every package resolves
through it). This module re-exports the SAME objects (identity, not copies),
per the facade contract. Requires scitex-dev with the primitive
(>=0.62.0); anything older fails loud with the floor, never a silent None.
"""

from __future__ import annotations

try:
    from scitex_dev.project import (
        ACTIVE_PROJECT_ENV,
        ACTIVE_PROJECT_FILENAME,
        ALL_PROJECTS,
        active_project_file,
        clear_active_project,
        resolve_project,
        set_active_project,
        validate_ref,
    )
except ImportError as e:  # pragma: no cover - resolved at install time
    raise ImportError(
        "scitex_sdk.project requires scitex-dev>=0.62.0 (active-project "
        "primitive). Install or upgrade scitex-dev; refusing to substitute "
        "a local reimplementation that would drift."
    ) from e

__all__ = [
    "ACTIVE_PROJECT_ENV",
    "ACTIVE_PROJECT_FILENAME",
    "ALL_PROJECTS",
    "active_project_file",
    "clear_active_project",
    "resolve_project",
    "set_active_project",
    "validate_ref",
]
