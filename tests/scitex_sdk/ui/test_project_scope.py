#!/usr/bin/env python3
"""Project scope precedence: an explicit project beats the last visited one."""

from scitex_sdk.ui.project_scope import LocalProjectProvider, resolve_project


def _provider(tmp_path, *folders):
    root = tmp_path / "projects"
    for name in folders:
        (root / name).mkdir(parents=True)
    return LocalProjectProvider(root)


def test_explicit_project_beats_last_visited(tmp_path):
    # Arrange
    provider = _provider(tmp_path, "dotfiles", "paper")
    provider.remember(None, "dotfiles")
    # Act
    resolved = resolve_project(None, provider, explicit="paper")
    # Assert
    assert resolved == "paper"


def test_explicit_project_becomes_last_visited(tmp_path):
    # Arrange
    provider = _provider(tmp_path, "dotfiles", "paper")
    provider.remember(None, "dotfiles")
    # Act
    resolve_project(None, provider, explicit="paper")
    # Assert
    assert provider.last_visited() == "paper"


def test_last_visited_is_used_without_explicit_project(tmp_path):
    # Arrange
    provider = _provider(tmp_path, "dotfiles", "paper")
    provider.remember(None, "paper")
    # Act
    resolved = resolve_project(None, provider)
    # Assert
    assert resolved == "paper"


def test_inaccessible_explicit_project_does_not_fall_back(tmp_path):
    # Arrange
    provider = _provider(tmp_path, "dotfiles")
    provider.remember(None, "dotfiles")
    # Act
    resolved = resolve_project(None, provider, explicit="someone-elses")
    # Assert
    assert resolved is None


def test_local_provider_skips_hidden_folders(tmp_path):
    # Arrange
    provider = _provider(tmp_path, ".cache", "paper")
    # Act
    ids = [entry.id for entry in provider.list_projects()]
    # Assert
    assert ids == ["paper"]


# EOF
