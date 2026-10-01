#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Tests for scitex_sdk.ui._mcp.server — MCP smoke + tool invocation."""

import asyncio
import json

import pytest

# fastmcp is an optional dep (scitex-ui[mcp]); skip the whole module if
# it isn't installed so pytest collection stays green (PA-303).
pytest.importorskip("fastmcp")

from scitex_sdk.ui._mcp.server import (  # noqa: E402
    mcp,
    ui_skills_get,
    ui_skills_list,
    ui_get_component,
    ui_list_components,
    ui_get_static_dir,
    ui_get_docs_path,
)


# ---------------------------------------------------------------------------
# Server / list_tools smoke
# ---------------------------------------------------------------------------


def test_server_name_is_scitex_ui():
    # Arrange
    # Act
    # Assert
    assert mcp.name == "scitex-ui"


def test_list_tools_includes_ui_skills_list():
    # Arrange
    tools = asyncio.run(mcp.list_tools())
    # Act
    names = {t.name for t in tools}
    # Assert
    assert "ui_skills_list" in names, f"missing ui_skills_list, got {names}"


def test_list_tools_includes_ui_skills_get():
    # Arrange
    tools = asyncio.run(mcp.list_tools())
    # Act
    names = {t.name for t in tools}
    # Assert
    assert "ui_skills_get" in names, f"missing ui_skills_get, got {names}"


def test_list_tools_includes_ui_get_component():
    # Arrange
    tools = asyncio.run(mcp.list_tools())
    # Act
    names = {t.name for t in tools}
    # Assert
    assert "ui_get_component" in names


def test_list_tools_includes_ui_list_components():
    # Arrange
    tools = asyncio.run(mcp.list_tools())
    # Act
    names = {t.name for t in tools}
    # Assert
    assert "ui_list_components" in names


def test_list_tools_includes_ui_get_static_dir():
    # Arrange
    tools = asyncio.run(mcp.list_tools())
    # Act
    names = {t.name for t in tools}
    # Assert
    assert "ui_get_static_dir" in names


def test_list_tools_includes_ui_get_docs_path():
    # Arrange
    tools = asyncio.run(mcp.list_tools())
    # Act
    names = {t.name for t in tools}
    # Assert
    assert "ui_get_docs_path" in names


# ---------------------------------------------------------------------------
# Tool descriptions
# ---------------------------------------------------------------------------


def test_list_tools_ui_skills_list_has_description():
    # Arrange
    # Act
    tools = asyncio.run(mcp.list_tools())
    tool_map = {t.name: t for t in tools}
    # Assert
    assert tool_map["ui_skills_list"].description


def test_list_tools_ui_skills_get_has_description():
    # Arrange
    # Act
    tools = asyncio.run(mcp.list_tools())
    tool_map = {t.name: t for t in tools}
    # Assert
    assert tool_map["ui_skills_get"].description


def test_list_tools_ui_get_component_has_description():
    # Arrange
    # Act
    tools = asyncio.run(mcp.list_tools())
    tool_map = {t.name: t for t in tools}
    # Assert
    assert tool_map["ui_get_component"].description


def test_list_tools_ui_list_components_has_description():
    # Arrange
    # Act
    tools = asyncio.run(mcp.list_tools())
    tool_map = {t.name: t for t in tools}
    # Assert
    assert tool_map["ui_list_components"].description


def test_list_tools_ui_get_static_dir_has_description():
    # Arrange
    # Act
    tools = asyncio.run(mcp.list_tools())
    tool_map = {t.name: t for t in tools}
    # Assert
    assert tool_map["ui_get_static_dir"].description


def test_list_tools_ui_get_docs_path_has_description():
    # Arrange
    # Act
    tools = asyncio.run(mcp.list_tools())
    tool_map = {t.name: t for t in tools}
    # Assert
    assert tool_map["ui_get_docs_path"].description


# ---------------------------------------------------------------------------
# Direct function invocation (sync) — exercises the JSON envelope contract
# ---------------------------------------------------------------------------


def test_ui_skills_list_success_is_true():
    # Arrange
    raw = ui_skills_list.fn() if hasattr(ui_skills_list, "fn") else ui_skills_list()
    # Act
    payload = json.loads(raw)
    # Assert
    assert payload["success"] is True


def test_ui_skills_list_package_is_scitex_ui():
    # Arrange
    raw = ui_skills_list.fn() if hasattr(ui_skills_list, "fn") else ui_skills_list()
    # Act
    payload = json.loads(raw)
    # Assert
    assert payload["package"] == "scitex-ui"


def test_ui_skills_list_skills_is_list():
    # Arrange
    raw = ui_skills_list.fn() if hasattr(ui_skills_list, "fn") else ui_skills_list()
    # Act
    payload = json.loads(raw)
    # Assert
    assert isinstance(payload["skills"], list)


def test_ui_skills_list_contains_python_api():
    # Arrange
    raw = ui_skills_list.fn() if hasattr(ui_skills_list, "fn") else ui_skills_list()
    # Act
    payload = json.loads(raw)
    # Assert
    assert "03_python-api" in payload["skills"]


def test_ui_skills_get_known_page_success_is_true():
    # Arrange
    fn = ui_skills_get.fn if hasattr(ui_skills_get, "fn") else ui_skills_get
    raw = fn(name="03_python-api")
    # Act
    payload = json.loads(raw)
    # Assert
    assert payload["success"] is True


def test_ui_skills_get_known_page_name_is_correct():
    # Arrange
    fn = ui_skills_get.fn if hasattr(ui_skills_get, "fn") else ui_skills_get
    raw = fn(name="03_python-api")
    # Act
    payload = json.loads(raw)
    # Assert
    assert payload["name"] == "03_python-api"


def test_ui_skills_get_content_is_string():
    # Arrange
    fn = ui_skills_get.fn if hasattr(ui_skills_get, "fn") else ui_skills_get
    raw = fn(name="03_python-api")
    # Act
    payload = json.loads(raw)
    # Assert
    assert isinstance(payload["content"], str)


def test_ui_skills_get_content_is_nonempty():
    # Arrange
    fn = ui_skills_get.fn if hasattr(ui_skills_get, "fn") else ui_skills_get
    raw = fn(name="03_python-api")
    # Act
    payload = json.loads(raw)
    # Assert
    assert payload["content"].strip(), "skill content must be non-empty"


def test_ui_skills_get_unknown_page_success_is_false():
    # Arrange
    fn = ui_skills_get.fn if hasattr(ui_skills_get, "fn") else ui_skills_get
    raw = fn(name="this-skill-does-not-exist")
    # Act
    payload = json.loads(raw)
    # Assert
    assert payload["success"] is False


def test_ui_skills_get_unknown_page_error_contains_available():
    # Arrange
    fn = ui_skills_get.fn if hasattr(ui_skills_get, "fn") else ui_skills_get
    raw = fn(name="this-skill-does-not-exist")
    # Act
    payload = json.loads(raw)
    # Assert
    assert "available" in payload["error"]


# ---------------------------------------------------------------------------
# End-to-end async tool invocation through the registered MCP machinery
# ---------------------------------------------------------------------------


def test_call_tool_ui_skills_list_success():
    # Arrange
    result = asyncio.run(mcp.call_tool("ui_skills_list", {}))
    text = result.content[0].text
    # Act
    payload = json.loads(text)
    # Assert
    assert payload["success"] is True


def test_call_tool_ui_skills_list_has_skills_key():
    # Arrange
    result = asyncio.run(mcp.call_tool("ui_skills_list", {}))
    text = result.content[0].text
    # Act
    payload = json.loads(text)
    # Assert
    assert "skills" in payload


def test_call_tool_ui_skills_get_success():
    # Arrange
    result = asyncio.run(mcp.call_tool("ui_skills_get", {"name": "03_python-api"}))
    text = result.content[0].text
    # Act
    payload = json.loads(text)
    # Assert
    assert payload["success"] is True


def test_call_tool_ui_skills_get_name_is_correct():
    # Arrange
    result = asyncio.run(mcp.call_tool("ui_skills_get", {"name": "03_python-api"}))
    text = result.content[0].text
    # Act
    payload = json.loads(text)
    # Assert
    assert payload["name"] == "03_python-api"


# ---------------------------------------------------------------------------
# §6 Python API parity tools — direct invocation
# ---------------------------------------------------------------------------


def test_ui_get_component_returns_metadata():
    # Arrange
    # Act
    raw = ui_get_component.fn() if hasattr(ui_get_component, "fn") else ui_get_component(name="app-shell")
    payload = json.loads(raw)
    # Assert
    assert payload["success"] is True


def test_ui_get_component_unknown_returns_error():
    # Arrange
    # Act
    raw = ui_get_component.fn() if hasattr(ui_get_component, "fn") else ui_get_component(name="nonexistent")
    payload = json.loads(raw)
    # Assert
    assert payload["success"] is False


def test_ui_list_components_returns_list():
    # Arrange
    # Act
    raw = ui_list_components.fn() if hasattr(ui_list_components, "fn") else ui_list_components()
    payload = json.loads(raw)
    # Assert
    assert isinstance(payload["components"], list)


def test_ui_list_components_includes_app_shell():
    # Arrange
    # Act
    raw = ui_list_components.fn() if hasattr(ui_list_components, "fn") else ui_list_components()
    payload = json.loads(raw)
    # Assert
    assert "app-shell" in payload["components"]


def test_ui_get_static_dir_returns_path():
    # Arrange
    # Act
    raw = ui_get_static_dir.fn() if hasattr(ui_get_static_dir, "fn") else ui_get_static_dir()
    payload = json.loads(raw)
    # Assert
    assert payload["success"] is True


def test_ui_get_docs_path_returns_path():
    # Arrange
    # Act
    raw = ui_get_docs_path.fn() if hasattr(ui_get_docs_path, "fn") else ui_get_docs_path()
    payload = json.loads(raw)
    # Assert
    assert payload["success"] is True


# ---------------------------------------------------------------------------
# §6 parity tools — end-to-end via MCP
# ---------------------------------------------------------------------------


def test_call_tool_ui_get_component_success():
    # Arrange
    result = asyncio.run(mcp.call_tool("ui_get_component", {"name": "app-shell"}))
    text = result.content[0].text
    # Act
    payload = json.loads(text)
    # Assert
    assert payload["success"] is True


def test_call_tool_ui_list_components_returns_list():
    # Arrange
    result = asyncio.run(mcp.call_tool("ui_list_components", {}))
    text = result.content[0].text
    # Act
    payload = json.loads(text)
    # Assert
    assert isinstance(payload["components"], list)


def test_call_tool_ui_get_static_dir_returns_path():
    # Arrange
    result = asyncio.run(mcp.call_tool("ui_get_static_dir", {}))
    text = result.content[0].text
    # Act
    payload = json.loads(text)
    # Assert
    assert payload["success"] is True


def test_call_tool_ui_get_docs_path_returns_path():
    # Arrange
    result = asyncio.run(mcp.call_tool("ui_get_docs_path", {}))
    text = result.content[0].text
    # Act
    payload = json.loads(text)
    # Assert
    assert payload["success"] is True


# EOF
