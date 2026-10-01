---
description: |
  [TOPIC] Shell Modules — App Shell, Status, Theme
  [DETAILS] Shell module reference — AppShell, StatusBar, ThemeProvider, RepoMonitor, Shortcuts, Custom Events, Vendor Assets. Companion to 31_shell-modules.md..
tags: [scitex-ui-shell-modules-app-shell]
---

# Shell Modules — App Shell, Status, Theme

See [31_shell-modules.md](31_shell-modules.md) for `initShell` entry point.

## `AppShell` + `Sidebar`

```typescript
import { AppShell, Sidebar } from "scitex-ui/ts/shell/app-shell";

// AppShellConfig
{
  sidebarWidth?: number,     // default: 250
  collapsible?: boolean,     // default: true
  startCollapsed?: boolean,  // default: false
  sidebarTitle?: string,
  sidebarIcon?: string,      // e.g. "fas fa-folder"
  accent?: string,           // preset key: "writer", "figrecipe"
  accentColor?: string,      // custom hex, overrides preset
  storageKey?: string,       // localStorage key for sidebar state
  onSidebarToggle?: (collapsed: boolean) => void,
}
```

## `StatusBar`

```typescript
import { StatusBar } from "scitex-ui/ts/shell/status-bar";

// StatusBarConfig
{
  items?: {
    left?: StatusItem[];    // { id, text, icon?, onClick?, title? }
    center?: StatusItem[];
    right?: StatusItem[];
  };
  showThemeToggle?: boolean;  // default: false
}
```

## `ThemeProvider`

```typescript
import { ThemeProvider } from "scitex-ui/ts/shell/theme-provider";

// ThemeProviderConfig
{
  defaultTheme?: "light" | "dark",    // default: "light"
  storageKey?: string,                 // default: "stx-theme"
  target?: HTMLElement,                // default: document.documentElement
  onThemeChange?: (theme) => void,
}
```

## `initRepoMonitor`

```typescript
import { initMonitorToggle, initRepoMonitor } from "scitex-ui/ts/shell/repo-monitor";

initMonitorToggle();  // idempotent; wires collapse/expand header

const client = initRepoMonitor({
  adapter: { fetchRecentFiles: () => fetch("/api/files").then(r => r.json()) },
  pollIntervalMs?: 10000,
});
// Returns RepoMonitorClient or null (if DOM elements missing)
client?.pause();
client?.resume();
```

## Keyboard Shortcuts Modal

```typescript
import { initKeyboardShortcuts, registerShortcuts, toggleShortcutsModal } from "scitex-ui/ts/shell/keyboard-shortcuts";

initKeyboardShortcuts();  // wires Alt+? and modal dismiss
registerShortcuts([
  { section: "Editor", label: "Save", keys: "Ctrl+S" },
]);
toggleShortcutsModal();
```

## Custom Events

| Event | When | `detail` |
|-------|------|----------|
| `stx-shell:command` | Toolbar/shortcut fires command | `{ command, data? }` |
| `stx-shell:files-changed` | AI tools create/modify files | — |
| `stx-shell:hidden-files-changed` | Hidden toggle | `{ showHidden }` |
| `stx-shell:camera` | Camera button clicked | — |
| `stx-shell:sketch` | Sketch button clicked | — |
| `stx-shell:mic-toggle` | Voice button clicked | — |
| `repo-monitor:toggle` | Monitor header toggled | `{ collapsed }` |

## Vendor Assets

- xterm.js (offline) at `/static/scitex_sdk/ui/vendor/xterm/`
- Monaco editor (offline) at `/static/scitex_sdk/ui/vendor/monaco-editor/`
