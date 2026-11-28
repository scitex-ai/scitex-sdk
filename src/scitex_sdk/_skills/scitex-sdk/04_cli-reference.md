---
description: [top-level command tree and config resolution] See SKILL.md workflow; component detail in scitex-app / scitex-ui skills.
tags: [scitex-sdk]
---

# SDK CLI reference (top level)

`scitex-sdk [--json] [--help-recursive] [COMMAND]` — every command also
accepts `-h/--help`; `--json` propagates to subcommands that honour it.

- `app` — App SDK: `init`, `validate`, `submit`, `file`, docs, skills,
  `mcp`, `list-python-apis` (see the scitex-app skill).
- `gui` — SDK wizard: `open` / `serve` / `status` / `stop`
  (`--port 31301` default; `--dry-run` previews).
- `ui` — UI shell: `lint`, `dev`, docs, skills, `mcp`,
  `list-python-apis` (see the scitex-ui skill).
- `docs`, `skills` — package documentation and agent-facing skills
  (`skills list` / `skills get <name>`).
- `mcp list-tools` — every MCP tool from both the app and ui servers.
- `api list` — the SDK's own declared operations + MCP tools with API
  contract rule findings (`--format json|csv|md`, `--json`, `--strict`).
  Any leaf gets the same command with
  `main.add_command(api_click_group(package="scitex-<pkg>"))`
  (`scitex_sdk.app.api_inventory`).
- `api inventory` — every endpoint and MCP tool of the installed ecosystem;
  with `--django-root/--django-settings/--asgi/--hosted-mcp` also a host's
  URLconf, ASGI mounts and hosted MCP, and with `--probe-base` a GET-only
  live probe. `--output-dir DIR` writes `inventory.json`, `inventory.csv`,
  `index.md`.
- `list-python-apis` — public API tree for both components (`--json`).
- `install-shell-completion`, `print-shell-completion` — TAB completion.

Config resolves per component group: `config.yaml` →
`$SCITEX_<GROUP>_CONFIG` → `~/.scitex/<group>/config.yaml` → defaults.
