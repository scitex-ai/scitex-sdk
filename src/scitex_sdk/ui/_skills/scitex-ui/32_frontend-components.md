---
description: |
  [TOPIC] SciTeX App Developer Guide
  [DETAILS] Frontend components reference — DataTable, FileBrowser, MediaViewer, ConfirmModal quick start and Bridge entry point.
tags: [scitex-ui-frontend-components]
---

# SciTeX App Developer Guide

How to build a SciTeX workspace app using `scitex-ui` components.
Reference implementation: [figrecipe](https://github.com/ywatanabe1989/figrecipe)

---

## 1. Quick Start

`bridge/bridge-init.ts` — entry point, auto-discovered by the workspace shell:

```typescript
import "@scitex/sdk/ui/css/app.css";
import { mountMyApp } from "./MountPoint";

const HANDLED_EXTS = [".myext"];

function init(): void {
  const mount = document.getElementById("app-mount");
  if (!mount) return;
  const opts = {
    container: mount,
    workingDir: mount.dataset.workingDir,
    darkMode: document.body.classList.contains("dark-theme"),
  };
  if (mount.dataset.embedded === "true") {
    mountMyApp(opts);
  } else {
    document.addEventListener("click", (e) => {
      const link = (e.target as Element)?.closest("[data-file-path]");
      const path = link?.getAttribute("data-file-path") || "";
      if (HANDLED_EXTS.includes(path.substring(path.lastIndexOf(".")))) {
        e.preventDefault(); e.stopPropagation();
        mountMyApp({ ...opts, initialFile: path });
      }
    });
  }
}
document.readyState === "loading"
  ? document.addEventListener("DOMContentLoaded", init)
  : init();
```

`bridge/MountPoint.ts`:

```typescript
import React from "react";
import { installFetchOverride, mountReactApp, unmountReactApp }
  from "@scitex/sdk/ui/react/app/bridge";
import type { BridgeConfig, BridgeMountOptions } from "@scitex/sdk/ui/react/app/bridge";
import { MyAppRoot } from "../MyAppRoot";

const CONFIG: BridgeConfig = {
  slug: "myapp",
  mountId: "app-mount",
  apiPaths: ["/api/files", "/api/save"],
  fileExtensions: [".myext"],
};

export function mountMyApp(options: BridgeMountOptions): void {
  installFetchOverride(CONFIG);
  mountReactApp(options.container, React.createElement(MyAppRoot, {
    apiBaseUrl: `/apps/${CONFIG.slug}/${CONFIG.slug}`,
    workingDir: options.workingDir,
    initialFile: options.initialFile,
    darkMode: options.darkMode,
  }));
}

export const unmountMyApp = unmountReactApp;
```

---

## 2. React Components

All imports from `scitex-ui/react/app/{component}`.

### DataTable

Full spreadsheet: multi-select, editing, clipboard, virtual scroll (>100 rows), sort, column resize.

```typescript
import { DataTable } from "@scitex/sdk/ui/react/app/data-table";
import type { Dataset } from "@scitex/sdk/ui/react/app/data-table";
// Dataset = { columns: string[]; rows: Array<{ [key: string]: string | number }> }
```

Key props: `data?: Dataset`, `csvContent?: string`, `readOnly?: boolean`,
`onDataChange?: (d: Dataset) => void`, `onCellSelect?: (pos: {row,col}) => void`,
`onStatusUpdate?: (msg: string) => void`, `showRowNumbers?`, `sortable?`, `resizable?`.

```tsx
<DataTable csvContent={rawCsv} onDataChange={(d) => save(d)} onStatusUpdate={setStatus} />
```

### FileBrowser

File tree with search, git badges, context menu, sort by name or mtime.

```typescript
import { FileBrowser } from "@scitex/sdk/ui/react/app/file-browser";
import type { FileNode } from "@scitex/sdk/ui/react/app/file-browser";
// FileNode = { name, path, type: "file"|"directory", children?, git_status?, mtime? }
```

Key props: `data?: FileNode[]`, `apiUrl?: string`, `onFileSelect?: (n: FileNode) => void`,
`onFileDoubleClick?`, `onContextAction?: (action, node) => void`,
`extensions?: string[] | null`, `searchable?: boolean`, `sortMode?: "name" | "mtime"`.

```tsx
<FileBrowser apiUrl="/api/file-tree" extensions={[".yaml"]} searchable
  onFileSelect={(n) => openFile(n.path)} />
```

### MediaViewer

Images (zoom/pan), PDFs, Mermaid, Graphviz, binary placeholder. Returns `null` for text files.

```typescript
import { MediaViewer } from "@scitex/sdk/ui/react/app/media-viewer";
// Props: filePath, getFileUrl(path,raw?,download?)=>string, fileType?, onDownload?
```

```tsx
<MediaViewer filePath={file} getFileUrl={(p, raw) => `/api/files${p}${raw ? "?raw=1" : ""}`} />
```

### ConfirmModal

```typescript
import { ConfirmModal } from "@scitex/sdk/ui/react/app/confirm-modal";
// Props: open, message, title?, confirmText?, cancelText?, onConfirm?, onCancel?
```

```tsx
<ConfirmModal open={show} message="Delete?" onConfirm={del} onCancel={() => setShow(false)} />
```

---

## See also
- [33_frontend-components-bridge.md](33_frontend-components-bridge.md) — Bridge infrastructure (BridgeConfig, fetch override, event bus) and `usePanelResize` hook
- [34_frontend-components-theme.md](34_frontend-components-theme.md) — CSS theme variables, reference implementation (figrecipe), packaging requirements
