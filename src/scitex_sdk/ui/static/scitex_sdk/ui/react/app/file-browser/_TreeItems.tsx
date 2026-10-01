/**
 * TreeItems — renders a list of file/folder nodes recursively.
 * Includes FolderItem which owns its own children container.
 *
 * Matches scitex-cloud _TreeRenderer.ts renderItems() + renderFolder() exactly:
 *   - Alphabetical sort (mirrors scitex-cloud default "name" sort mode)
 *   - Folders: .stx-app-file-tree__item.stx-app-file-tree__folder + .stx-app-file-tree__children.expanded indent guides
 *   - Files:   .stx-app-file-tree__item.stx-app-file-tree__file (delegated to FileItem)
 *   - Chevron: .stx-app-file-tree__chevron span (Unicode ▸ rendered via CSS ::before)
 *   - Spacer:  .stx-app-file-tree__spacer span (for empty-toggle folders)
 */

import React from "react";
import type { FileNode } from "./types";
import { FileItem } from "./_FileItem";

interface SharedProps {
  expanded: Set<string>;
  activeFile: string | null;
  showHidden: boolean;
  extensions: string[] | null;
  onToggle: (path: string) => void;
  onSelect: (node: FileNode) => void;
  onDoubleClick?: (node: FileNode) => void;
  searchMatches?: Set<string>;
  searchAncestors?: Set<string>;
  searchActive?: boolean;
  /** Sort mode — 'name' (A-Z) or 'mtime' (newest first) */
  sortMode?: "name" | "mtime";
}

/* ──────────────────────────────────────────────────────────── */
/* FolderItem                                                    */
/* ──────────────────────────────────────────────────────────── */

interface FolderItemProps extends SharedProps {
  node: FileNode;
}

const FolderItem: React.FC<FolderItemProps> = ({
  node,
  expanded,
  activeFile,
  showHidden,
  extensions,
  onToggle,
  onSelect,
  onDoubleClick,
  searchMatches,
  searchAncestors,
  searchActive,
  sortMode,
}) => {
  const isExpanded = expanded.has(node.path);
  const hasChildren = !!(node.children && node.children.length > 0);

  const classes = ["stx-app-file-tree__item", "stx-app-file-tree__folder"];
  if (isExpanded) classes.push("expanded");
  if (searchActive) {
    if (searchMatches?.has(node.path))
      classes.push("stx-app-file-tree__search-match");
    else if (searchAncestors?.has(node.path))
      classes.push("stx-app-file-tree__search-ancestor");
    else classes.push("stx-app-file-tree__search-dim");
  }

  return (
    <>
      {/* Folder row — matches scitex-cloud renderFolder() exactly */}
      <div
        className={classes.join(" ")}
        data-path={node.path}
        draggable={true}
        style={{ paddingLeft: 8 }}
        onClick={(e) => {
          e.stopPropagation();
          onToggle(node.path);
        }}
      >
        {/* Folder toggle button */}
        <button
          type="button"
          className="stx-app-file-tree__folder-toggle"
          data-action="toggle"
          data-path={node.path}
        >
          {hasChildren ? (
            <span
              className={`stx-app-file-tree__chevron${isExpanded ? " expanded" : ""}`}
            />
          ) : (
            <span className="stx-app-file-tree__spacer" />
          )}
          {/* Icon — hidden by CSS: .stx-app-file-tree__icon { display: none } */}
          <span className="stx-app-file-tree__icon" />
        </button>
        {/* Folder name — blue #6cb6ff via .stx-app-file-tree__folder > .stx-app-file-tree__name */}
        <span className="stx-app-file-tree__name">{node.name}</span>
      </div>

      {/* Children container — CSS handles indent guides */}
      {hasChildren && (
        <div
          className={`stx-app-file-tree__children${isExpanded ? " expanded" : ""}`}
          style={isExpanded ? undefined : { display: "none" }}
        >
          <TreeItems
            nodes={node.children!}
            expanded={expanded}
            activeFile={activeFile}
            showHidden={showHidden}
            extensions={extensions}
            onToggle={onToggle}
            onSelect={onSelect}
            onDoubleClick={onDoubleClick}
            searchMatches={searchMatches}
            searchAncestors={searchAncestors}
            searchActive={searchActive}
            sortMode={sortMode}
          />
        </div>
      )}
    </>
  );
};

/* ──────────────────────────────────────────────────────────── */
/* TreeItems                                                     */
/* ──────────────────────────────────────────────────────────── */

export interface TreeItemsProps extends SharedProps {
  nodes: FileNode[];
}

export const TreeItems: React.FC<TreeItemsProps> = ({
  nodes,
  expanded,
  activeFile,
  showHidden,
  extensions,
  onToggle,
  onSelect,
  onDoubleClick,
  searchMatches,
  searchAncestors,
  searchActive,
  sortMode = "name",
}) => {
  const filtered = nodes.filter((n) => {
    if (!showHidden && n.name.startsWith(".")) return false;
    if (n.type === "file" && extensions) {
      const ext = "." + n.name.split(".").pop();
      if (!extensions.includes(ext)) return false;
    }
    return true;
  });

  // Sort — alphabetical or by mtime, no directory/file separation
  const sorted = [...filtered].sort((a, b) => {
    if (sortMode === "mtime") {
      return (b.mtime ?? 0) - (a.mtime ?? 0);
    }
    // Default: alphabetical (case-insensitive), dirs and files interleaved
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
  });

  return (
    <>
      {sorted.map((node) =>
        node.type === "directory" ? (
          <FolderItem
            key={node.path}
            node={node}
            expanded={expanded}
            activeFile={activeFile}
            showHidden={showHidden}
            extensions={extensions}
            onToggle={onToggle}
            onSelect={onSelect}
            onDoubleClick={onDoubleClick}
            searchMatches={searchMatches}
            searchAncestors={searchAncestors}
            searchActive={searchActive}
            sortMode={sortMode}
          />
        ) : (
          <FileItem
            key={node.path}
            node={node}
            activeFile={activeFile}
            onSelect={onSelect}
            onDoubleClick={onDoubleClick}
            searchMatches={searchMatches}
            searchActive={searchActive}
          />
        ),
      )}
    </>
  );
};
