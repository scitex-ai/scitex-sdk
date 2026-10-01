/**
 * TreeUtils - Utility functions for tree operations
 * Ported from scitex-cloud (no API deps)
 */

import type { TreeItem } from "../types";

export class TreeUtils {
  static findItem(path: string, treeData: TreeItem[]): TreeItem | null {
    const search = (items: TreeItem[]): TreeItem | null => {
      for (const item of items) {
        if (item.path === path) return item;
        if (item.children) {
          const found = search(item.children);
          if (found) return found;
        }
      }
      return null;
    };
    return search(treeData);
  }

  static pathExistsInTree(targetPath: string, items: TreeItem[]): boolean {
    for (const item of items) {
      if (item.path === targetPath) return true;
      if (item.children && item.children.length > 0) {
        if (TreeUtils.pathExistsInTree(targetPath, item.children)) return true;
      }
    }
    return false;
  }

  static getParentPaths(path: string): string[] {
    const parts = path.split("/");
    const parents: string[] = [];
    for (let i = 1; i < parts.length; i++) {
      parents.push(parts.slice(0, i).join("/"));
    }
    return parents;
  }

  static getAllFilePaths(items: TreeItem[]): string[] {
    const paths: string[] = [];
    const traverse = (items: TreeItem[]): void => {
      for (const item of items) {
        if (item.type === "file") paths.push(item.path);
        if (item.children) traverse(item.children);
      }
    };
    traverse(items);
    return paths;
  }
}
