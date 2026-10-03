#!/usr/bin/env python3
"""Explicit-local backend selection: backend='local'/'filesystem' works.

An explicit local name selects the filesystem backend even when ambient
SCITEX_API_TOKEN exists; backend=None keeps cloud auto-selection; custom
registration semantics (register wins, unknown names KeyError) are unchanged.
"""

from __future__ import annotations

from scitex_sdk.app.sdk import get_files, register_backend
from scitex_sdk.app.sdk._filesystem import FileSystemBackend


def test_explicit_local_with_token_present_selects_filesystem(tmp_path, monkeypatch):
    # Arrange
    monkeypatch.setenv("SCITEX_API_TOKEN", "token-present")
    # Act
    files = get_files(tmp_path, backend="local")
    files.write("probe.txt", "local-wins")
    # Assert
    assert isinstance(files, FileSystemBackend) and files.read("probe.txt") == "local-wins"


def test_explicit_filesystem_name_selects_filesystem(tmp_path, monkeypatch):
    # Arrange
    monkeypatch.delenv("SCITEX_API_TOKEN", raising=False)
    # Act
    files = get_files(tmp_path, backend="filesystem")
    # Assert
    assert isinstance(files, FileSystemBackend)


def test_token_absent_default_selects_filesystem(tmp_path, monkeypatch):
    # Arrange
    monkeypatch.delenv("SCITEX_API_TOKEN", raising=False)
    # Act
    files = get_files(tmp_path)
    # Assert
    assert isinstance(files, FileSystemBackend)


def test_custom_backend_registration_still_wins(tmp_path):
    # Arrange
    sentinel = FileSystemBackend(tmp_path)
    register_backend("local", lambda root=None, **kwargs: sentinel)
    try:
        # Act
        files = get_files(tmp_path, backend="local")
    finally:
        from scitex_sdk.app.sdk import _registry
        from scitex_sdk.app.sdk import _local_files_factory

        _registry["local"] = _local_files_factory
    # Assert
    assert files is sentinel


def test_unknown_backend_still_keyerror(tmp_path):
    # Arrange
    import pytest
    # Act
    # Assert
    with pytest.raises(KeyError):
        get_files(tmp_path, backend="no-such-backend")


# EOF
