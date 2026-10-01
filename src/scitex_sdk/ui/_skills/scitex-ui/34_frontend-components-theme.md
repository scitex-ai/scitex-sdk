---
description: |
  [TOPIC] Frontend Components — Theme, Reference & Packaging
  [DETAILS] CSS theme variables, figrecipe reference implementation, WorkspaceResizeContext, and packaging requirements for bridge apps.
tags: [scitex-ui-frontend-components-theme]
---

# Frontend Components — Theme, Reference & Packaging

## 5. CSS Theme Variables

```typescript
import "@scitex/sdk/ui/css/app.css"; // provides all tokens
```

Never hardcode colors. Use semantic variables:

```css
/* Text */
color: var(--text-primary);  color: var(--text-secondary);  color: var(--text-muted);

/* Backgrounds */
background: var(--bg-page);
background: var(--workspace-bg-primary);   /* panel backgrounds */
background: var(--workspace-bg-elevated);  /* floating surfaces */

/* Borders */
border-color: var(--workspace-border-default);
border-color: var(--workspace-border-subtle);
border-color: var(--workspace-border-hover);

/* Status */
color: var(--status-success);  color: var(--status-warning);  color: var(--status-error);

/* App accent (declare per-app in theme.css) */
color: var(--app-accent-myapp);
background: var(--app-accent-myapp-tint);

/* Sizing */
width: var(--ui-collapsed-pane-width);  /* 48px collapsed panel */
font-size: var(--icon-md);              /* 16px */
```

Dark/light is `<html data-theme="dark|light">` on the shell — no app code needed.

---

## 6. Reference Implementation

**figrecipe** — [github.com/ywatanabe1989/figrecipe](https://github.com/ywatanabe1989/figrecipe)

All paths under `src/figrecipe/_django/frontend/src/`:

| File | What it demonstrates |
|------|----------------------|
| `bridge/bridge-init.ts` | Embedded vs standalone branching, init pattern |
| `bridge/MountPoint.ts` | BridgeConfig, fetch override, React root mount |
| `bridge/EventBus.ts` | Typed event helpers wrapping emitBridgeEvent/onBridgeEvent |
| `bridge/WorkspaceIntegration.ts` | WorkspaceResizeContext cross-boundary propagation |
| `FigrecipeEditor.tsx` | Root component with inner usePanelResize layout |

### WorkspaceResizeContext (advanced — optional)

Register inner panels so shell-level resize can propagate across the app boundary:

```typescript
import { useWorkspaceResize }
  from "@scitex/sdk/ui/react/shell/workspace/WorkspaceResizeContext";

const { registerPane, unregisterPane } = useWorkspaceResize();

useEffect(() => {
  registerPane({
    id: "myapp-sidebar",
    getWidth: () => panel.width,
    setWidth: (w) => { if (panel.panelRef.current) panel.panelRef.current.style.width = `${w}px`; },
    minWidth: 40,
    collapse: panel.toggleCollapse,
    isCollapsed: () => panel.collapsed,
  });
  return () => unregisterPane("myapp-sidebar");
}, [panel.width, panel.collapsed]);
```

Only needed when your app's inner resizers should push/pull shell column widths.

## 7. Packaging Requirement for Bridge Apps

Apps with a `bridge` key in `_django/manifest.json` must keep `_django/frontend/src/` in their source tree. scitex-hub discovers bridge paths by scanning sibling directories for `manifest.json` files, so the frontend TypeScript source must be present in the repo.

**For pip packaging**, use an `[app]` optional extra for Python dependencies needed by the platform integration:

```toml
[project.optional-dependencies]
app = [
    "django>=4.2.0",
    "Pillow>=9.0.0",
    "scitex-app>=0.1.0",
    "scitex-ui>=0.1.0",
]
```

**For CI**, clone the app repo as a sibling directory so the bridge discovery finds `manifest.json` and `frontend/src/`. Not all apps are pip packages, so sibling cloning is the standard approach.

## See also
- [32_frontend-components.md](32_frontend-components.md) — Quick start, React components (DataTable, FileBrowser, MediaViewer, ConfirmModal)
- [33_frontend-components-bridge.md](33_frontend-components-bridge.md) — Bridge infrastructure and usePanelResize hook
