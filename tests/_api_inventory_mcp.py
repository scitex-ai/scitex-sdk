"""A real FastMCP server for the notes test leaf: derived tools plus one legacy tool."""

from fastmcp import FastMCP

from scitex_sdk.app.api_mcp import register_fastmcp
from tests._api_ops_leaf import PLUGIN

mcp = FastMCP("notes")
register_fastmcp(mcp, PLUGIN)


@mcp.tool()
def notes_notes_legacy_dump(limit: int = 3) -> dict:
    """A hand-written tool with no operation behind it (double-prefixed)."""
    return {"limit": limit}


hosted = FastMCP("umbrella")
hosted.mount(mcp, namespace="notes")
