/**
 * FileBrowser — React port of scitex-cloud WorkspaceFilesTree component.
 *
 * Produces IDENTICAL DOM structure and CSS classes to scitex-cloud.
 * Source: scitex-cloud/static/shared/ts/components/stx-app-file-tree/
 *
 * Top-level DOM:
 *   <div class="stx-app-file-tree">
 *     <div class="stx-app-file-tree__content">
 *       <div class="stx-app-file-tree__tree">
 *         <div class="stx-app-file-tree__item stx-app-file-tree__root" />   ← hidden by CSS
 *         ... tree items ...
 *       </div>
 *     </div>
 *     <div class="stx-app-file-tree__search-box">...</div>    ← when searchable=true
 *   </div>
 */

import React, { useState, useCallback, useEffect, useRef } from "react";
import type { FileBrowserProps, FileNode } from "./types";
import { TreeItems } from "./_TreeItems";
import { ContextMenu, type ContextAction } from "./_ContextMenu";

/* ──────────────────────────────────────────────────────────── */
/* Helpers                                                       */
/* ──────────────────────────────────────────────────────────── */

function countFiles(nodes: FileNode[]): number {
  let count = 0;
  for (const node of nodes) {
    if (node.type === "file") count++;
    if (node.children) count += countFiles(node.children);
  }
  return count;
}

/** Filter tree recursively — keep parents of matching children */
function filterTree(nodes: FileNode[], query: string): FileNode[] {
  if (!query) return nodes;
  const lq = query.toLowerCase();
  const result: FileNode[] = [];
  for (const node of nodes) {
    if (node.type === "directory" && node.children) {
      const filtered = filterTree(node.children, query);
      if (node.name.toLowerCase().includes(lq) || filtered.length > 0) {
        result.push({
          ...node,
          children: filtered.length > 0 ? filtered : node.children,
        });
      }
    } else if (node.name.toLowerCase().includes(lq)) {
      result.push(node);
    }
  }
  return result;
}

/** Build search match sets — mirrors scitex-cloud SearchHandler.getMatchInfo */
function buildSearchInfo(
  nodes: FileNode[],
  lq: string,
): { matches: Set<string>; ancestors: Set<string> } {
  const matches = new Set<string>();
  const ancestors = new Set<string>();

  function visit(items: FileNode[]): boolean {
    let anyMatch = false;
    for (const node of items) {
      const nameMatch = node.name.toLowerCase().includes(lq);
      if (node.type === "directory" && node.children) {
        const childMatch = visit(node.children);
        if (childMatch) {
          ancestors.add(node.path);
          anyMatch = true;
        }
        if (nameMatch) anyMatch = true;
      } else if (nameMatch) {
        matches.add(node.path);
        anyMatch = true;
      }
    }
    return anyMatch;
  }

  visit(nodes);
  return { matches, ancestors };
}

function findNode(nodes: FileNode[], path: string): FileNode | null {
  for (const n of nodes) {
    if (n.path === path) return n;
    if (n.children) {
      const found = findNode(n.children, path);
      if (found) return found;
    }
  }
  return null;
}

/* ──────────────────────────────────────────────────────────── */
/* FileBrowser                                                   */
/* ──────────────────────────────────────────────────────────── */

export const FileBrowser: React.FC<FileBrowserProps> = ({
  data: propData,
  apiUrl,
  onFileSelect,
  onDirectoryToggle,
  extensions = null,
  showHidden = false,
  showImageBadge: _showImageBadge = true,
  showFileCount = false,
  searchable = false,
  onContextAction,
  sortMode = "name",
  onFileDoubleClick,
  className,
  style,
}) => {
  const [data, setData] = useState<FileNode[]>(propData ?? []);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchVisible, setSearchVisible] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    node: FileNode;
  } | null>(null);

  // Ctrl+K — ported from scitex-cloud WorkspaceKeyboardHandler
  useEffect(() => {
    if (!searchable) return;
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setSearchVisible((v) => {
          if (!v) setTimeout(() => searchInputRef.current?.focus(), 50);
          else setSearchQuery("");
          return !v;
        });
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [searchable]);

  useEffect(() => {
    if (propData) setData(propData);
  }, [propData]);

  useEffect(() => {
    if (!apiUrl) return;
    setLoading(true);
    fetch(apiUrl)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => {
        setData(Array.isArray(d) ? d : (d.tree ?? d.children ?? []));
        setLoading(false);
      })
      .catch((e: Error) => {
        setError(e.message);
        setLoading(false);
      });
  }, [apiUrl]);

  const handleToggle = useCallback(
    (path: string) => {
      setExpanded((prev) => {
        const next = new Set(prev);
        const wasExpanded = next.has(path);
        if (wasExpanded) next.delete(path);
        else next.add(path);
        if (onDirectoryToggle) {
          const node = findNode(data, path);
          if (node) onDirectoryToggle(node, !wasExpanded);
        }
        return next;
      });
    },
    [data, onDirectoryToggle],
  );

  const handleSelect = useCallback(
    (node: FileNode) => {
      setActiveFile(node.path);
      onFileSelect?.(node);
    },
    [onFileSelect],
  );

  // Search info
  const searchActive = !!(searchQuery && searchQuery.length > 0);
  const { matches: searchMatches, ancestors: searchAncestors } = searchActive
    ? buildSearchInfo(data, searchQuery.toLowerCase())
    : { matches: new Set<string>(), ancestors: new Set<string>() };

  const filteredData = searchActive ? filterTree(data, searchQuery) : data;

  // Loading / error states
  if (loading) {
    return (
      <div
        className={`stx-app-file-tree${className ? ` ${className}` : ""}`}
        style={style}
      >
        <div className="stx-app-file-tree__content">
          <div className="stx-app-file-tree__loading">
            <i className="fas fa-spinner fa-spin" /> Loading files...
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`stx-app-file-tree${className ? ` ${className}` : ""}`}
        style={style}
      >
        <div className="stx-app-file-tree__content">
          <div className="stx-app-file-tree__error">
            <i className="fas fa-exclamation-triangle" />
            <span>{error}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`stx-app-file-tree${className ? ` ${className}` : ""}`}
      style={style}
      onContextMenu={
        onContextAction
          ? (e) => {
              const item = (e.target as HTMLElement).closest(
                ".stx-app-file-tree__item",
              ) as HTMLElement | null;
              if (!item) return;
              e.preventDefault();
              const path = item.dataset.path;
              if (!path) return;
              const node = findNode(data, path);
              if (node) setContextMenu({ x: e.clientX, y: e.clientY, node });
            }
          : undefined
      }
    >
      {/* Content wrapper — mirrors scitex-cloud .stx-app-file-tree__content */}
      <div className="stx-app-file-tree__content">
        {showFileCount && (
          <div className="stx-app-file-tree__file-count">
            {countFiles(data)} file{countFiles(data) !== 1 ? "s" : ""}
          </div>
        )}

        {/* Tree root — mirrors scitex-cloud .stx-app-file-tree__tree */}
        <div className="stx-app-file-tree__tree">
          {/* Root item — hidden by CSS: .stx-app-file-tree__item.stx-app-file-tree__root { display: none } */}
          <div
            className="stx-app-file-tree__item stx-app-file-tree__root"
            data-path=""
            data-action="select-root"
            style={{ paddingLeft: 8 }}
          >
            <span className="stx-app-file-tree__icon" />
            <span className="stx-app-file-tree__name stx-app-file-tree__root-name">
              Project
            </span>
          </div>

          {filteredData.length === 0 ? (
            <div
              className="stx-app-file-tree__loading"
              style={{
                padding: "16px 12px",
                fontSize: 12,
                color: "var(--color-fg-muted, #768390)",
                fontStyle: "italic",
              }}
            >
              {searchActive ? "No matching files" : "No files to display"}
            </div>
          ) : (
            <TreeItems
              nodes={filteredData}
              expanded={expanded}
              activeFile={activeFile}
              showHidden={showHidden}
              extensions={extensions}
              onToggle={handleToggle}
              onSelect={handleSelect}
              onDoubleClick={onFileDoubleClick}
              searchMatches={searchMatches}
              searchAncestors={searchAncestors}
              searchActive={searchActive}
              sortMode={sortMode}
            />
          )}
        </div>
      </div>

      {/* Search box — mirrors scitex-cloud .stx-app-file-tree__search-box */}
      {searchable && searchVisible && (
        <div className="stx-app-file-tree__search-box">
          <div className="stx-app-file-tree__search-input-wrapper">
            <span className="stx-app-file-tree__search-icon">
              <i className="fas fa-search" />
            </span>
            <input
              ref={searchInputRef}
              className="stx-app-file-tree__search-input"
              type="text"
              placeholder="Filter files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape") {
                  setSearchQuery("");
                  setSearchVisible(false);
                }
              }}
            />
            {searchQuery && (
              <button
                className="stx-app-file-tree__search-clear"
                onClick={() => setSearchQuery("")}
                title="Clear (Esc)"
              >
                <i className="fas fa-times" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Context menu */}
      {contextMenu && onContextAction && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          node={contextMenu.node}
          onAction={(action: ContextAction) => {
            onContextAction(action, contextMenu.node);
            setContextMenu(null);
          }}
          onClose={() => setContextMenu(null)}
        />
      )}
    </div>
  );
};
