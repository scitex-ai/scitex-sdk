#!/usr/bin/env python3
"""Component metadata registry."""

from __future__ import annotations
from typing import Any, Optional

_COMPONENTS: dict[str, Any] = {}


def register_component(name: str, metadata: Any) -> None:
    """Register a frontend component's metadata."""
    _COMPONENTS[name] = metadata


def get_component(name: str) -> Optional[Any]:
    """Get metadata for a registered component."""
    return _COMPONENTS.get(name)


def list_components() -> list[str]:
    """List all registered component names."""
    return sorted(_COMPONENTS.keys())
