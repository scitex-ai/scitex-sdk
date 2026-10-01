#!/usr/bin/env python3
"""MCP server for scitex-sdk ui — skills and documentation via Model Context Protocol.

fastmcp is the OPTIONAL ``[mcp]`` extra and this module is that extra's whole
surface, so the distribution is imported under a guard (PS-233) and is NOT
promoted into ``[project.dependencies]``. Serving MCP is a capability a
consumer of the UI components must be able to install without; making fastmcp
core would put it on every install of a Django/React component library.

The guard degrades in a defined way rather than with a silent ``pass``:

* the module stays importable without fastmcp, and each tool function below is
  still defined and callable as a plain Python function;
* ``FASTMCP_AVAILABLE`` is the caller-visible answer to "is the capability
  present" — ``scitex-sdk ui mcp start`` / ``mcp list-tools`` check it and report
  the install command (exit 1, as documented in their help specs) instead of
  crashing on a half-built server;
* ``run_server()`` refuses with :data:`INSTALL_HINT` rather than letting an
  AttributeError escape from a ``None``.

``_AbsentFastMCP`` is what ``mcp`` binds to when the extra is missing: its
``tool()`` decorator returns the function unchanged (the DEFINITIONS do not
need fastmcp, the REGISTRATION does), and everything that would actually serve
raises. Nothing is swallowed — running an MCP server without fastmcp still
fails loudly, it just no longer makes the module unimportable.
"""

from __future__ import annotations

import json as _json_mod

try:
    from fastmcp import FastMCP
except ImportError:  # optional extra `[mcp]` — PS-233 guard
    FastMCP = None  # type: ignore[assignment,misc]

#: Whether the optional ``[mcp]`` extra is importable in this environment.
FASTMCP_AVAILABLE: bool = FastMCP is not None

#: Shown when something tries to serve without the extra installed.
INSTALL_HINT = (
    "The SDK UI MCP server needs the optional `mcp` extra: "
    "pip install 'scitex-sdk[mcp]'"
)


class _AbsentFastMCP:
    """Stand-in for ``FastMCP`` when the optional ``[mcp]`` extra is absent.

    Deliberately not a fake server: registration is a no-op so the module and
    its tool functions still import, and every serving entry point raises with
    :data:`INSTALL_HINT`.
    """

    def tool(self, *args, **kwargs):
        """No-op registration — returns the decorated function unchanged."""

        def _register(fn):
            return fn

        return _register

    def run(self, *args, **kwargs):
        raise RuntimeError(INSTALL_HINT)

    async def list_tools(self, *args, **kwargs):
        raise RuntimeError(INSTALL_HINT)


if FastMCP is None:  # optional extra absent — see FASTMCP_AVAILABLE
    mcp = _AbsentFastMCP()
else:
    mcp = FastMCP("scitex-ui")


def _json(obj):
    """Serialize to JSON string."""
    return _json_mod.dumps(obj, indent=2, default=str)


# =============================================================================
# Skills Tools
# =============================================================================


# §5 — skills introspection tools (per audit-mcp-tools convention)
@mcp.tool()
def ui_skills_list() -> str:
    """List the names of every skill page shipped by scitex-ui.

    Returns
    -------
        JSON string with `{"success": true, "package": "scitex-ui",
        "skills": ["01_python-api", "02_cli", ...]}`.
    """
    try:
        from pathlib import Path

        skills_dir = Path(__file__).parent.parent / "_skills" / "scitex-ui"
        names = sorted(p.stem for p in skills_dir.glob("*.md") if p.name != "SKILL.md")
        return _json_mod.dumps(
            {"success": True, "package": "scitex-ui", "skills": names},
            indent=2,
        )
    except Exception as e:
        return _json_mod.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
def ui_skills_get(name: str) -> str:
    """Fetch the full Markdown content of one scitex-sdk ui skill page.

    Args:
        name: Skill page name without `.md`, e.g. `01_python-api`.

    Returns
    -------
        JSON string with `{"success": true, "package": "scitex-ui",
        "name": <name>, "content": <markdown>}`, or an error envelope.
    """
    try:
        from pathlib import Path

        skills_dir = Path(__file__).parent.parent / "_skills" / "scitex-ui"
        target = skills_dir / f"{name}.md"
        if not target.exists():
            available = sorted(
                p.stem for p in skills_dir.glob("*.md") if p.name != "SKILL.md"
            )
            return _json_mod.dumps(
                {
                    "success": False,
                    "error": f"unknown skill {name!r}; available: {available}",
                },
                indent=2,
            )
        return _json_mod.dumps(
            {
                "success": True,
                "package": "scitex-ui",
                "name": name,
                "content": target.read_text(encoding="utf-8"),
            },
            indent=2,
        )
    except Exception as e:
        return _json_mod.dumps({"success": False, "error": str(e)}, indent=2)


# =============================================================================
# Python API Parity Tools (§6)
# =============================================================================


@mcp.tool()
def ui_get_component(name: str) -> str:
    """Get metadata for a registered component by name.

    Args:
        name: Component name, e.g. ``app-shell``.

    Returns
    -------
        JSON string with component metadata, or ``{"success": false, ...}``
        if the component is not found.
    """
    try:
        from scitex_sdk.ui._registry import get_component

        meta = get_component(name)
        if meta is None:
            return _json_mod.dumps(
                {"success": False, "error": f"component {name!r} not found"},
                indent=2,
            )
        cls = meta
        result = {
            "name": cls.name,
            "version": cls.version,
            "description": cls.description,
            "ts_entry": cls.ts_entry,
            "css_file": cls.css_file,
        }
        return _json_mod.dumps({"success": True, "component": result}, indent=2)
    except Exception as e:
        return _json_mod.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
def ui_list_components() -> str:
    """List the names of every registered frontend component.

    Returns
    -------
        JSON string with ``{"success": true, "components": [...]}``.
    """
    try:
        from scitex_sdk.ui._registry import list_components

        names = list_components()
        return _json_mod.dumps(
            {"success": True, "components": names}, indent=2
        )
    except Exception as e:
        return _json_mod.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
def ui_get_static_dir() -> str:
    """Return the absolute path to scitex-ui's static asset directory.

    Returns
    -------
        JSON string with ``{"success": true, "path": "..."}``.
    """
    try:
        from scitex_sdk.ui import get_static_dir

        path = str(get_static_dir())
        return _json_mod.dumps({"success": True, "path": path}, indent=2)
    except Exception as e:
        return _json_mod.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
def ui_get_docs_path() -> str:
    """Return the absolute path to scitex-ui's bundled documentation directory.

    Returns
    -------
        JSON string with ``{"success": true, "path": "..."}``.
    """
    try:
        from scitex_sdk.ui import get_docs_path

        path = str(get_docs_path())
        return _json_mod.dumps({"success": True, "path": path}, indent=2)
    except Exception as e:
        return _json_mod.dumps({"success": False, "error": str(e)}, indent=2)


# =============================================================================
# Server Entry Point
# =============================================================================


def run_server(transport: str = "stdio") -> None:
    """Run the MCP server.

    Raises RuntimeError carrying the install command when the optional ``[mcp]``
    extra is absent. Keeping this module importable is the guard's job; serving
    without fastmcp is still a loud failure, never a no-op.
    """
    if not FASTMCP_AVAILABLE:
        raise RuntimeError(INSTALL_HINT)
    mcp.run(transport=transport)


if __name__ == "__main__":
    run_server()


# EOF
