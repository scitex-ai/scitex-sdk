---
description: |
  [TOPIC] scitex-sdk ui Shell Modules
  [DETAILS] TypeScript shell framework — initShell entry point, ShellConfig, and adapter interfaces. Use when wiring the workspace shell to a backend..
tags: [scitex-ui-shell-modules]
---

# scitex-sdk ui Shell Modules

Vanilla TypeScript workspace shell. All imports from `scitex-ui/ts/shell`.

See companion sub-skills:
- [35_shell-modules-reference.md](35_shell-modules-reference.md) — ShellFileTree, Toolbar, Terminal, Viewer, Chat
- [36_shell-modules-app-shell.md](36_shell-modules-app-shell.md) — AppShell, StatusBar, ThemeProvider, RepoMonitor, Shortcuts, Events, Vendor

## Entry Point: `initShell(config)`

```typescript
import { initShell } from "scitex-ui/ts/shell";

const instances = await initShell({
  fileTree: {
    adapter: { fetchTree: () => fetch("/api/tree").then(r => r.json()).then(d => d.tree) },
    onFileSelect: (node) => console.log(node.path),
    showHidden: false,
    extensions: null,  // null = all file types
  },
  terminal: {
    adapter: { getWebSocketUrl: () => `ws://127.0.0.1:${port + 1}/` },
    clipboard: true,
    reconnectDelay: 3000,
  },
  toolbar: {
    keybindingMode: "emacs",
  },
  viewer: {
    adapter: {
      readFile: (p) => fetch(`/api/file/${p}`).then(r => r.json()),
      getFileUrl: (p) => `/api/file/${p}?raw=true`,
    },
  },
});
// instances: { fileTree?, toolbar?, shortcuts?, viewer? }
```

All sections are optional — omit to skip that module.

## `ShellConfig` Interface

```typescript
interface ShellConfig {
  fileTree?: {
    adapter: FileTreeAdapter;
    onFileSelect?: (node: FileNode) => void;
    showHidden?: boolean;
    extensions?: string[] | null;
  };
  terminal?: {
    adapter: TerminalConnectionAdapter;
    clipboard?: boolean;
    dragDrop?: boolean;
    onFileDrop?: (files: FileList) => Promise<string[]>;
    reconnectDelay?: number;
  };
  toolbar?: ToolbarConfig;
  chat?: { adapter: ChatAdapter; autoSpeak?: boolean };
  viewer?: {
    adapter: ViewerAdapter;
    onFileOpen?: (file: OpenFile) => void;
  };
}
```

## Adapter Interfaces

### `FileTreeAdapter`

```typescript
interface FileTreeAdapter {
  fetchTree(): Promise<FileNode[]>;
  createFile?(parentPath: string, name: string): Promise<void>;
  createFolder?(parentPath: string, name: string): Promise<void>;
  deleteItem?(path: string): Promise<void>;
  renameItem?(oldPath: string, newName: string): Promise<void>;
}

interface FileNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FileNode[];
  git_status?: string;
  mtime?: number;
}
```

### `TerminalConnectionAdapter`

```typescript
interface TerminalConnectionAdapter {
  getWebSocketUrl(): string;
  onStatusChange?(state: "connecting" | "connected" | "disconnected" | "error"): void;
  onMessage?(data: string, inst: TerminalInstance): string | null;
}
```

### `ViewerAdapter`

```typescript
interface ViewerAdapter {
  readFile(path: string): Promise<{ content: string; language?: string }>;
  saveFile?(path: string, content: string): Promise<void>;
  getFileUrl(path: string): string;
  getFileApiUrl?(path: string): string;
}
```

### `ChatAdapter`

```typescript
interface ChatAdapter {
  streamChat(message: string, context?: AiContext, images?: string[]): Promise<Response>;
  fetchCurrentModel?(): Promise<{ model: string; display?: string; campaign?: boolean } | null>;
  speak?(text: string): void;
}
```

### `RepoMonitorAdapter`

```typescript
interface RepoMonitorAdapter {
  fetchRecentFiles(): Promise<RecentFileEntry[]>;
}
interface RecentFileEntry {
  path: string;
  mtime: number;
  event?: string;
}
```
