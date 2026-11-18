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

## GUI configuration

`gui serve` and `gui open` read the selected SDK configuration for `host` and
`port`. Select one file, without merging files, in this order:

1. `scitex-sdk gui --config PATH serve` (or `open`).
2. A nonempty `SCITEX_SDK_CONFIG` path.
3. An existing `.scitex/sdk/config.yaml` in the nearest Git project, using
   `scitex_config._ecosystem.local_state.path` discovery.
4. `$SCITEX_DIR/sdk/config.yaml`, defaulting to `~/.scitex/sdk/config.yaml`.

The shared resolver walks up to the nearest Git boundary. It does not select
an outer project's configuration across a nested Git repository. An arbitrary
`./config.yaml` is not read automatically; select it explicitly with `--config`
when intended. Reading does not create or rewrite the configuration file.

```yaml
gui:
  host: localhost
  port: 31302
```

Each value uses the owning `PriorityConfig` cascade: explicit `--host`/`--port`,
then the selected YAML `gui` key, then `SCITEX_SDK_GUI_HOST` /
`SCITEX_SDK_GUI_PORT`, then the command defaults `127.0.0.1` / `31301`.
The YAML port must be an unquoted integer; environment ports are converted to
integers. Effective ports must be 1–65535. Hosts must be nonempty strings
without surrounding whitespace.

Only `gui.host` and `gui.port` are supported in this reader. Other keys inside
`gui` refuse, including `force` and `allow_remote`. Other root sections are not
consumed by this reader. File configuration cannot authorize a non-loopback
bind: `--allow-remote` still has to be passed on the command line. Process
control flags keep their existing command-line behavior.

Missing default files use the command/environment/default cascade without creation. A missing explicitly
selected file, broken explicit symlink, malformed YAML or invalid GUI schema
refuses without falling back to another file. An empty or null document uses
the remaining value cascade. The selected GUI schema is validated before
applying command overrides; an override does not hide an invalid GUI schema.
`gui --help`, command help, `status` and `stop` do not load the GUI YAML file,
so those recovery paths remain usable with damaged configuration.

```bash
scitex-sdk gui --config ./sdk.yaml serve --dry-run --json
scitex-sdk gui open --port 31303 --dry-run --json
```

Owners: `_gui_config.py::resolve_gui_options`, `cli.py::{gui_serve,gui_open}`;
shared parsing, path discovery and value precedence remain in `scitex-config`.
Actual subprocess CLI controls, including guards and read-only symlinks, live
in `tests/integration/test_gui_configuration.py`; existing command contracts
live in `tests/scitex_sdk/test_cli_gui.py` and `test_cli_root.py`.
An already-running wizard follows the existing reuse behavior; new host/port
settings apply to a new launch. Dry-run tests do not start a server or
establish a rendered/deployed GUI.

## Configuration scope still incomplete

This GUI reader does not implement a generic YAML chain for the root, App or
UI groups or their other commands. That integration remains outstanding;
creating their conventional files does not establish consumption.

For `app install-dev . --dry-run`, `--server` overrides `SCITEX_SERVER_URL`,
then the default `http://127.0.0.1:8000`; the GUI configuration above does not
select that server. Actual installation still requires the normal validation
and authorization workflow. Other SDK helpers and peers have their own
readers: inspect the owning implementation before extending these scoped
contracts into package-wide configuration claims.
