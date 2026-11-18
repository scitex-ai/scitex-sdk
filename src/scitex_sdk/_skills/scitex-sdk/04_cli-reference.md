---
description: [top-level command tree and configuration limits] See SKILL.md workflow; component detail in scitex-app / scitex-ui skills.
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

## Configuration reader scope

The root, App and UI group entrypoints do not implement the advertised generic
`config.yaml` / `SCITEX_<GROUP>_CONFIG` / `~/.scitex/<group>/config.yaml`
resolution chain. Wiring the shared ecosystem configuration contract remains
an implementation gap. Creating those files or setting a configuration-path
variable alone does not establish that a command consumes it.

Use the actual command's declared options and environment readers:

- `gui serve --dry-run --json` shows the default host127.0.0.1/port31301;
  `--host` and `--port` select explicit values. The selected GUI command does
  not consume those YAML files or a `SCITEX_SDK_CONFIG` path.
- `app install-dev . --dry-run` previews its server without contacting it.
  `--server` overrides `SCITEX_SERVER_URL`, then the default
  `http://127.0.0.1:8000`. Real installation additionally requires the normal
  authorization and validation workflow.
- Other SDK commands, runtime helpers, linters and peers can have their own
  readers; check the owning implementation rather than extending these two
  command-specific results into a package-wide configuration claim.

Owning readers: `cli.py::gui_serve` and
`app/_cli/_app.py::app_install_dev`. Both remain unchanged by this guide.
The root/App/UI callbacks set Click context and dispatch commands; mentioning
configuration paths in help is not a loader or a precedence test.
