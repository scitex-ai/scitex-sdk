---
name: scitex-ui
description: |
  [WHAT] Shared frontend framework for SciTeX web apps — vanilla TS workspace shell + optional React components + Django static-asset integration.
  [WHEN] Use when user asks to build a SciTeX workspace app, add panel resizing, share a React DataTable, theme with design tokens, set up Django static asset discovery, inspect a DOM element, or mentions initShell, usePanelResize, Bridge infrastructure.
  [HOW] `pip install scitex-sdk[gui,chat,mcp,cli]` then `import scitex_sdk.ui`; see leaf skills for details.
tags: [scitex-ui]
allowed-tools: mcp__scitex__ui_*
primary_interface: mixed
interfaces:
  python: 2
  cli: 1
  mcp: 2
  skills: 2
  http: 2
---

# scitex-sdk ui — Workspace Shell Framework

> **Interfaces:** Python ⭐⭐ · CLI ⭐ · MCP ⭐⭐ · Skills ⭐⭐ · Hook — · HTTP ⭐⭐

> Read the SDK workflow skill first, then use Python, CLI or MCP for execution.

Reusable frontend framework for SciTeX workspace apps.
**Shell = vanilla TypeScript. App content = React (optional).**

## Installation & import

```python
import scitex_sdk.ui                # pip install scitex-sdk[gui,chat,mcp,cli]
# or:  import scitex.ui         # pip install scitex  (umbrella)
```

The App/UI component skills are bundled by scitex-sdk; begin with the SDK workflow skill.

## Sub-skills

### Mandatory (SK105–108)
- [01_installation.md](01_installation.md) — pip install + Django static-asset wiring + smoke verify
- [02_quick-start.md](02_quick-start.md) — wire shell into a Django template
- [03_python-api.md](03_python-api.md) — Python registry + static-asset resolver
- [04_cli-reference.md](04_cli-reference.md) — full `scitex-sdk ui` subcommand surface

### Legacy core (renumbered)
- [12_python-api.md](12_python-api.md) — original Python API page (was 01)
- [13_cli.md](13_cli.md) — original CLI page (was 02)

### Standards (20–29)
- [20_css-theme.md](20_css-theme.md) — CSS design tokens, theme variables, dark/light mode

### Architecture (30–39)
- [30_shell-framework.md](30_shell-framework.md) — Workspace shell framework overview
- [31_shell-modules.md](31_shell-modules.md) — `initShell`, ShellConfig, adapter interfaces
- [32_frontend-components.md](32_frontend-components.md) — React components quick start (DataTable, FileBrowser, MediaViewer)
- [33_frontend-components-bridge.md](33_frontend-components-bridge.md) — Bridge infrastructure + usePanelResize
- [34_frontend-components-theme.md](34_frontend-components-theme.md) — CSS theme, figrecipe reference, packaging
- [35_shell-modules-reference.md](35_shell-modules-reference.md) — ShellFileTree, Toolbar, Terminal, Viewer, Chat
- [36_shell-modules-app-shell.md](36_shell-modules-app-shell.md) — AppShell, StatusBar, ThemeProvider, RepoMonitor, Shortcuts, Events, Vendor

### Doctrine + lint
- [40_component-usage-doctrine.md](40_component-usage-doctrine.md) — UI-101..107 component-usage rules + `scitex-sdk ui lint` walker
- [41_dual-mode-mounting.md](41_dual-mode-mounting.md) — run one app standalone AND as a scitex-hub built-in: the mount-prefix contract, and why both halves refuse to guess `/`
- [42_mobile-panes.md](42_mobile-panes.md) — `{% scitex_panes %}`: multi-column apps become one pane per screen with tabs on phones; `stxPanes.show()`, `.stx-acc`

## Architecture

```
ts/shell/          ← Vanilla TS workspace shell (single source of truth)
ts/app/            ← Vanilla TS app components
react/app/         ← React app components (usePanelResize, DataTable)
css/shell/         ← Shell CSS
templates/         ← Django HTML templates
```

## MCP Tools

Exposed via the umbrella `scitex` MCP server (registered by `scitex._mcp_tools.ui.register_ui_tools`):

| Tool | Purpose |
|------|---------|
| `ui_inspect_element` | Introspect one DOM element in the live playwright-cli browser — bbox, computed styles, attrs, parent chain, matching CSS rules |
| `ui_inspect_elements` | Bulk-inspect all elements matching a selector (with `limit`) |
| `ui_notify` | Send a UI-level alert via scitex-notification (audio / desktop / email / webhook / Telegram / Twilio fallback) |
| `ui_get_notification_config` | Show active notification config (fallback order, level routing, timeouts) |

Standalone `scitex-sdk ui mcp` server also exposes:

| Tool | Purpose |
|------|---------|
| `skills_list` | List available skill pages |
| `skills_get` | Get a skill page by name |
