/**
 * TreeContextMenuInit - Ported from scitex-cloud (no API deps)
 */
import type { ContextMenuHandler } from "./ContextMenuHandler";

export function initContextMenu(
  container: HTMLElement,
  contextMenuHandler: ContextMenuHandler,
): void {
  container.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    const target = e.target as HTMLElement;
    const item = target.closest(".wft-item[data-path]");
    if (item) {
      const path = item.getAttribute("data-path");
      const isDir =
        item.classList.contains("wft-folder") ||
        item.classList.contains("wft-root") ||
        path === "";
      const gitStatusCode = item.getAttribute("data-git-status");
      const gitStaged = item.getAttribute("data-git-staged") === "true";
      const gitStatus = gitStatusCode
        ? { status: gitStatusCode, staged: gitStaged }
        : undefined;
      contextMenuHandler.show(
        e.clientX,
        e.clientY,
        path || "",
        isDir,
        gitStatus,
      );
    } else {
      const treeArea = target.closest(".wft-tree, .workspace-files-tree");
      if (treeArea) contextMenuHandler.showForRoot(e.clientX, e.clientY);
    }
  });
  const sidebar = container.closest(".stx-shell-sidebar");
  const toolbar = sidebar?.querySelector(":scope > .stx-shell-sidebar__header");
  if (toolbar) {
    toolbar.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      contextMenuHandler.showForRoot(
        (e as MouseEvent).clientX,
        (e as MouseEvent).clientY,
      );
    });
  }
  document.addEventListener("repo-monitor:contextmenu", ((e: CustomEvent) => {
    const { path, x, y } = e.detail;
    contextMenuHandler.show(x, y, path, false, undefined);
  }) as EventListener);
}
