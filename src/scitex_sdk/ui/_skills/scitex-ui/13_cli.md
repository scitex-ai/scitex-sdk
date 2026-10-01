---
description: |
  [TOPIC] scitex-sdk ui CLI
  [DETAILS] scitex-sdk ui CLI reference — MCP server, docs, skills subcommands..
tags: [scitex-ui-cli]
---

# scitex-sdk ui CLI

Entry point: `scitex-ui` (requires `pip install scitex-sdk[gui,chat,mcp,cli]`).

## MCP Server

```bash
scitex-sdk ui mcp start           # Start MCP server (stdio transport)
scitex-sdk ui mcp doctor          # Check dependencies and server health
scitex-sdk ui mcp list-tools      # List available MCP tools
scitex-sdk ui mcp list-tools -v   # With one-line descriptions
scitex-sdk ui mcp list-tools -vv  # With full descriptions
scitex-sdk ui mcp list-tools --json  # JSON output
scitex-sdk ui mcp installation    # Show Claude Code settings.json snippet
```

### Claude Code Integration

```json
{
  "mcpServers": {
    "scitex-ui": {
      "command": "scitex-ui",
      "args": ["mcp", "start"]
    }
  }
}
```

Add to `~/.claude/settings.json`.

## Skills

```bash
scitex-sdk ui skills list              # List available skill pages
scitex-sdk ui skills get               # Get main SKILL.md
scitex-sdk ui skills get shell-modules # Get a named sub-skill page
```

Available skill names: `python-api`, `shell-modules`, `frontend-components`, `css-theme`, `cli`.

## Documentation

```bash
scitex-sdk ui docs    # Open or display bundled Sphinx docs
```

## Global Options

```bash
scitex-sdk ui --version           # Show version (e.g. 0.4.2)
scitex-sdk ui --help              # Show help
scitex-sdk ui --help-recursive    # Show help for all subcommands
```

## Installation

```bash
pip install scitex-sdk[gui,chat,mcp,cli]           # base package
pip install scitex-sdk[gui,chat,mcp,cli]      # + CLI (click, scitex-dev)
pip install scitex-sdk[gui,chat,mcp,cli]      # + MCP server (fastmcp)
pip install scitex-sdk[gui,chat,mcp,cli]      # everything
```
