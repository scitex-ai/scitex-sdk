/**
 * FileItem — single file row in the workspace files tree.
 * Matches scitex-cloud _TreeRenderer.ts renderFile() output exactly.
 *
 * DOM structure produced:
 *   <div class="stx-app-file-tree__item stx-app-file-tree__file [selected] [stx-app-file-tree__search-*]" data-path="..." draggable>
 *     <span class="stx-app-file-tree__spacer" />       ← spacer (no chevron for files)
 *     <span class="stx-app-file-tree__icon" />         ← hidden by CSS
 *     <span class="stx-app-file-tree__name">filename</span>
 *   </div>
 */

import React from "react";
import type { FileNode } from "./types";

export interface FileItemProps {
  node: FileNode;
  activeFile: string | null;
  onSelect: (node: FileNode) => void;
  onDoubleClick?: (node: FileNode) => void;
  searchMatches?: Set<string>;
  searchActive?: boolean;
}

export const FileItem: React.FC<FileItemProps> = ({
  node,
  activeFile,
  onSelect,
  onDoubleClick,
  searchMatches,
  searchActive,
}) => {
  const isSelected = node.path === activeFile || node.is_current;

  const classes = ["stx-app-file-tree__item", "stx-app-file-tree__file"];
  if (isSelected) classes.push("selected");
  if (searchActive) {
    if (searchMatches?.has(node.path))
      classes.push("stx-app-file-tree__search-match");
    else classes.push("stx-app-file-tree__search-dim");
  }

  return (
    <div
      className={classes.join(" ")}
      data-path={node.path}
      data-action="select"
      draggable={true}
      style={{ paddingLeft: 8 }}
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", node.path);
        e.dataTransfer.effectAllowed = "copy";
      }}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(node);
      }}
      onDoubleClick={
        onDoubleClick
          ? (e) => {
              e.stopPropagation();
              onDoubleClick(node);
            }
          : undefined
      }
    >
      {/* Spacer — scitex-cloud: files use stx-app-file-tree__spacer, not chevron */}
      <span className="stx-app-file-tree__spacer" />
      {/* Icon — hidden by CSS: .stx-app-file-tree__icon { display: none } */}
      <span className="stx-app-file-tree__icon" />
      {/* File name */}
      <span className="stx-app-file-tree__name">{node.name}</span>
    </div>
  );
};
