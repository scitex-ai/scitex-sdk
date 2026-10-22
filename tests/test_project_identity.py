"""Project-primitive identity tests — scitex_sdk.project must be the SAME
objects as scitex_dev.project (identity, not copies), per the facade
contract. Requires scitex-dev with the primitive (>=0.62.0).
"""

from __future__ import annotations

import pytest

scitex_dev_project = pytest.importorskip(
    "scitex_dev.project",
    reason="requires scitex-dev>=0.62.0 (project primitive)",
)

from scitex_sdk import project as facade  # noqa: E402


def test_project_names_are_identical():
    # Arrange
    names = facade.__all__
    # Act
    mismatched = [
        name
        for name in names
        if getattr(facade, name) is not getattr(scitex_dev_project, name)
    ]
    # Assert
    assert mismatched == []


def test_resolve_through_facade_explicit():
    # Arrange
    explicit = "scitex-04/dotfiles"
    # Act
    resolved = facade.resolve_project(explicit=explicit)
    # Assert
    assert resolved == "scitex-04/dotfiles"


def test_resolve_through_facade_all():
    # Arrange
    explicit = "all"
    # Act
    resolved = facade.resolve_project(explicit=explicit)
    # Assert
    assert resolved == "all"


def test_resolve_through_facade_rejects_bare():
    # Arrange
    explicit = "bare"
    # Act
    # Assert
    with pytest.raises(ValueError):
        facade.resolve_project(explicit=explicit)
