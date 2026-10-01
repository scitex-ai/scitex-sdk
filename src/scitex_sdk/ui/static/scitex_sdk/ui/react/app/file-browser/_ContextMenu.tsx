/**
 * ContextMenu — right-click context menu for file tree items.
 * Matches scitex-cloud .stx-app-file-tree__context-menu DOM structure exactly.
 *
 * DOM structure produced:
 *   <div class="stx-app-file-tree__context-menu" style="position:fixed; top:y; left:x">
 *     <div class="stx-app-file-tree__context-item context-new-file">...</div>
 *     <div class="stx-app-file-tree__context-item context-rename">...</div>
 *     <div class="stx-app-file-tree__context-item context-duplicate">...</div>
 *     <div class="stx-app-file-tree__context-item">Copy Path</div>
 *     <div class="stx-app-file-tree__context-separator" />
 *     <div class="stx-app-file-tree__context-item context-delete">...</div>
 *   </div>
 */

import React, { useEffect } from "react";
import type { FileNode } from "./types";

export type ContextAction =
  | "new"
  | "rename"
  | "delete"
  | "duplicate"
  | "copy-path";

export interface ContextMenuProps {
  x: number;
  y: number;
  node: FileNode;
  onAction: (action: ContextAction) => void;
  onClose: () => void;
}

export const ContextMenu: React.FC<ContextMenuProps> = ({
  x,
  y,
  node,
  onAction,
  onClose,
}) => {
  const isDir = node.type === "directory";

  useEffect(() => {
    const handler = () => onClose();
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, [onClose]);

  return (
    <div
      className="stx-app-file-tree__context-menu"
      style={{ position: "fixed", top: y, left: x, zIndex: 10000 }}
      onClick={(e) => e.stopPropagation()}
    >
      {isDir && (
        <div
          className="stx-app-file-tree__context-item context-new-file"
          onClick={() => onAction("new")}
        >
          <span className="stx-app-file-tree__context-icon">
            <i className="fas fa-plus" />
          </span>
          <span className="stx-app-file-tree__context-label">New File</span>
        </div>
      )}
      <div
        className="stx-app-file-tree__context-item context-rename"
        onClick={() => onAction("rename")}
      >
        <span className="stx-app-file-tree__context-icon">
          <i className="fas fa-pen" />
        </span>
        <span className="stx-app-file-tree__context-label">Rename</span>
      </div>
      <div
        className="stx-app-file-tree__context-item context-duplicate"
        onClick={() => onAction("duplicate")}
      >
        <span className="stx-app-file-tree__context-icon">
          <i className="fas fa-copy" />
        </span>
        <span className="stx-app-file-tree__context-label">Duplicate</span>
      </div>
      <div className="stx-app-file-tree__context-item" onClick={() => onAction("copy-path")}>
        <span className="stx-app-file-tree__context-icon">
          <i className="fas fa-clipboard" />
        </span>
        <span className="stx-app-file-tree__context-label">Copy Path</span>
      </div>
      <div className="stx-app-file-tree__context-separator" />
      <div
        className="stx-app-file-tree__context-item context-delete"
        onClick={() => onAction("delete")}
      >
        <span className="stx-app-file-tree__context-icon">
          <i className="fas fa-trash" />
        </span>
        <span className="stx-app-file-tree__context-label">Delete</span>
      </div>
    </div>
  );
};
