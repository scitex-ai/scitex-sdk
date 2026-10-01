---
description: |
  [TOPIC] Frontend Components — Bridge & Panel Resize
  [DETAILS] Bridge infrastructure (BridgeConfig, installFetchOverride, mount/unmount, event bus) and usePanelResize hook.
tags: [scitex-ui-frontend-components-bridge]
---

# Frontend Components — Bridge & Panel Resize

## 3. Bridge Infrastructure

All exports from `scitex-ui/react/app/bridge`.

### BridgeConfig

```typescript
interface BridgeConfig {
  slug: string;           // must match Django app slug
  mountId: string;        // DOM element id, e.g. "app-mount"
  apiPaths: string[];     // path prefixes to rewrite (e.g. ["/api/", "/save"])
  fileExtensions: string[]; // handled file types (e.g. [".yaml"])
}
```

### installFetchOverride(config)

Patches `window.fetch` once per slug. Paths matching any `apiPaths` prefix are rewritten:

```
/api/save  →  /apps/{slug}/{slug}/api/save
```

Safe to call multiple times. Must run before any API fetch.

### mountReactApp / unmountReactApp

```typescript
mountReactApp(container: HTMLElement, element: React.ReactElement): void
unmountReactApp(): void   // tears down React root
```

`mountReactApp` always unmounts the previous root first.

### emitBridgeEvent / onBridgeEvent

Slug-namespaced `CustomEvent` bus on `document`. Full event name: `{slug}:{eventName}`.

```typescript
emitBridgeEvent<T>(slug: string, eventName: string, detail: T): void
onBridgeEvent<T>(slug: string, eventName: string, handler: (d: T) => void): () => void
// returns cleanup fn — return it from useEffect
```

```typescript
emitBridgeEvent("myapp", "fileSelect", { path: "/data.yaml" });
const cleanup = onBridgeEvent("myapp", "fileSelect", ({ path }) => load(path));
```

---

## 4. Panel Resize Hook

```typescript
import { usePanelResize } from "@scitex/sdk/ui/react/app/usePanelResize";
```

Config (all required except `maxWidth`, `containerRef`, `onBoundaryOverflow`):

```typescript
{
  direction: "left" | "right",  // "left" = resizer on right side of panel
  minWidth: number,             // auto-collapse below this
  defaultWidth: number,
  storageKey: string,           // localStorage key for width
  collapseKey: string,          // localStorage key for collapsed state
  maxWidth?: number,
  containerRef?: React.RefObject<HTMLElement>,  // prevents pushing siblings off-screen
  onBoundaryOverflow?: (px: number, dir: "left"|"right") => void,
}
```

Returns: `{ width, collapsed, panelRef, resizerProps, headerProps, toggleCollapse }`

```tsx
const containerRef = useRef<HTMLDivElement>(null);
const panel = usePanelResize({
  direction: "left", minWidth: 40, defaultWidth: 280,
  storageKey: "myapp-sidebar-w", collapseKey: "myapp-sidebar-c", containerRef,
});

<div ref={containerRef} style={{ display: "flex", height: "100%" }}>
  <aside ref={panel.panelRef as React.RefObject<HTMLDivElement>}
         style={{ width: panel.collapsed ? 40 : panel.width }}>
    <header {...panel.headerProps}>Files</header>
    <FileBrowser ... />
  </aside>
  <div className="resizer" {...panel.resizerProps} />
  <main style={{ flex: 1 }}>...</main>
</div>
```

Width and collapsed state persist via localStorage. Double-click resizer or header to toggle.

---

## See also
- [32_frontend-components.md](32_frontend-components.md) — Quick start, React components (DataTable, FileBrowser, MediaViewer, ConfirmModal)
- [34_frontend-components-theme.md](34_frontend-components-theme.md) — CSS theme variables, reference implementation, packaging requirements
