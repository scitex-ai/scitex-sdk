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
- `list-python-apis` — public API tree for both components (`--json`).
- `install-shell-completion`, `print-shell-completion` — TAB completion.

Config resolves per component group: `config.yaml` →
`$SCITEX_<GROUP>_CONFIG` → `~/.scitex/<group>/config.yaml` → defaults.
