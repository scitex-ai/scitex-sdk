/**
 * SearchHandler - Ported from scitex-cloud (no API deps)
 */
import type { TreeItem } from "../types";

export class SearchHandler {
  private searchQuery: string = "";
  constructor(
    private onSearchChange: () => void,
    private getTreeData: () => TreeItem[],
  ) {}

  setQuery(query: string): void {
    this.searchQuery = query.toLowerCase().trim();
    this.onSearchChange();
  }
  getQuery(): string {
    return this.searchQuery;
  }
  clear(): void {
    this.searchQuery = "";
    this.onSearchChange();
  }
  isActive(): boolean {
    return this.searchQuery.length > 0;
  }
  matches(item: TreeItem): boolean {
    if (!this.searchQuery) return true;
    return item.name.toLowerCase().includes(this.searchQuery);
  }

  filterTree(items: TreeItem[]): TreeItem[] {
    if (!this.searchQuery) return items;
    return this.filterRecursive(items);
  }

  private filterRecursive(items: TreeItem[]): TreeItem[] {
    const result: TreeItem[] = [];
    for (const item of items) {
      if (item.type === "directory" && item.children) {
        const filteredChildren = this.filterRecursive(item.children);
        if (this.matches(item) || filteredChildren.length > 0)
          result.push({
            ...item,
            children:
              filteredChildren.length > 0 ? filteredChildren : item.children,
          });
      } else {
        if (this.matches(item)) result.push(item);
      }
    }
    return result;
  }

  getMatchInfo(items: TreeItem[]): {
    matches: Set<string>;
    ancestors: Set<string>;
  } {
    const matches = new Set<string>();
    const ancestors = new Set<string>();
    if (this.searchQuery) this.buildMatchInfo(items, matches, ancestors);
    return { matches, ancestors };
  }

  private buildMatchInfo(
    items: TreeItem[],
    matches: Set<string>,
    ancestors: Set<string>,
  ): boolean {
    let hasMatch = false;
    for (const item of items) {
      if (this.matches(item)) {
        matches.add(item.path);
        hasMatch = true;
      }
      if (item.type === "directory" && item.children) {
        const childHasMatch = this.buildMatchInfo(
          item.children,
          matches,
          ancestors,
        );
        if (childHasMatch) {
          ancestors.add(item.path);
          hasMatch = true;
        }
      }
    }
    return hasMatch;
  }

  getMatchingItems(): TreeItem[] {
    if (!this.searchQuery) return [];
    const matches: TreeItem[] = [];
    this.collectMatches(this.getTreeData(), matches);
    return matches;
  }

  private collectMatches(items: TreeItem[], matches: TreeItem[]): void {
    for (const item of items) {
      if (this.matches(item) && item.type === "file") matches.push(item);
      if (item.type === "directory" && item.children)
        this.collectMatches(item.children, matches);
    }
  }
}
