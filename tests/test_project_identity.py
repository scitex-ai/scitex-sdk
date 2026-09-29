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
    for name in facade.__all__:
        assert getattr(facade, name) is getattr(scitex_dev_project, name), (
            f"scitex_sdk.project.{name!r} is not identical to "
            f"scitex_dev.project.{name!r}"
        )


def test_resolve_through_facade():
    assert (
        facade.resolve_project(explicit="scitex-04/dotfiles")
        == "scitex-04/dotfiles"
    )
    assert facade.resolve_project(explicit="all") == "all"
    with pytest.raises(ValueError):
        facade.resolve_project(explicit="bare")
