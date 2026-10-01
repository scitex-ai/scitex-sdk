---
description: |
  [TOPIC] Shell Modules Reference
  [DETAILS] Shell module reference — ShellFileTree, Toolbar, Terminal, Viewer, Chat. Companion to 31_shell-modules.md..
tags: [scitex-ui-shell-modules-reference]
---

# Shell Modules Reference

See [31_shell-modules.md](31_shell-modules.md) for `initShell` entry point and adapter interfaces.

## `ShellFileTree`

```typescript
import { ShellFileTree } from "scitex-ui/ts/shell/file-tree";

const tree = new ShellFileTree({
  container: "#ws-worktree-tree",  // default
  adapter: myAdapter,
  onFileSelect?: (node) => void,
  onDirectoryToggle?: (node, expanded) => void,
  showHidden?: boolean,
  extensions?: string[] | null,
  showGitStatus?: boolean,
  showFolderActions?: boolean,
});
await tree.load();
tree.refresh();          // reload from backend
tree.select(path);       // select by path
tree.getExpanded();      // string[]
tree.toggleHidden();     // toggles dotfiles, persists to localStorage
tree.destroy();
```

System noise always hidden: `.DS_Store`, `Thumbs.db`, `__pycache__`, `node_modules`, `.venv`, `venv`.

Event: `document.dispatchEvent("stx-shell:hidden-files-changed", { detail: { showHidden } })`.

## `ToolbarManager` + `KeyboardShortcuts`

```typescript
import { ToolbarManager, KeyboardShortcuts } from "scitex-ui/ts/shell/toolbar";

// Commands dispatch as CustomEvent on document:
// document.addEventListener("stx-shell:command", (e) => {
//   console.log(e.detail.command, e.detail.data);
// });

// Built-in commands: "save", "delete", "commit", "run", "new-file",
// "new-folder", "rename", "theme-toggle", "next-tab", "prev-tab",
// "new-terminal", "next-terminal", "prev-terminal",
// "shortcuts-editor", "shortcuts-terminal", "copy-terminal"

interface ToolbarConfig {
  buttons?: ButtonBinding[];        // { elementId, command, data? }[]
  shortcuts?: KeyShortcut[];        // { key, ctrlKey?, command, mode? }[]
  keybindingMode?: string;          // default: "emacs"
  keybindingModeSelector?: string;  // default: "keybinding-mode"
}
```

## `initTerminal`

```typescript
import { initTerminal } from "scitex-ui/ts/shell/terminal";

await initTerminal({
  container: "#stx-shell-ai-console-terminal",  // default
  adapter: myTerminalAdapter,
  clipboard?: boolean,      // default: true
  dragDrop?: boolean,       // default: false
  onFileDrop?: (files) => Promise<string[]>,
  reconnectDelay?: number,  // default: 3000ms
  autoInit?: boolean,       // default: true
});
```

Requires xterm.js vendor bundle at `/static/scitex_sdk/ui/vendor/xterm/`.

## `ViewerManager`

```typescript
import { ViewerManager, detectFileType } from "scitex-ui/ts/shell/viewer";

const viewer = new ViewerManager({
  container?: string | HTMLElement,      // default: "#ws-viewer-content"
  tabsContainer?: string | HTMLElement,  // default: "#ws-viewer-tabs"
  adapter: myViewerAdapter,
  onFileOpen?: (file: OpenFile) => void,
  onFileSave?: (path: string) => void,
});

// Supported FileType values:
// "text" | "image" | "pdf" | "csv" | "mermaid" | "graphviz" | "audio" | "video" | "binary"
const type = detectFileType("/path/to/file.png");  // => "image"
```

Viewer sub-components: `ImageViewer`, `PdfViewer`, `CsvViewer`, `AudioViewer`,
`VideoViewer`, `MermaidViewer`, `GraphvizViewer`, `MarkdownPreviewPanel`.

PDF requires PDF.js. Monaco/syntax highlighting loaded on demand.

## Chat Module

```typescript
import {
  processStream, renderMarkdown,
  saveMessage, loadMessages, clearMessages,
  loadHistory, pushHistory,
  VoiceRecorder, WebcamCapture, SketchCanvas, ImageInputManager,
  ChatMode, chatSend, SessionsPanel,
} from "scitex-ui/ts/shell/chat";
```

`processStream` handles SSE streaming from `ChatAdapter.streamChat()`, renders markdown, appends tool-use tags, and optionally speaks via TTS.
