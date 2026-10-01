/**
 * DirectoryFilterHandler - Ported from scitex-cloud (no API deps)
 */
import type { TreeItem } from "../types";

export class DirectoryFilterHandler {
  private directoryFilter: string | null = null;
  private filteredTreeData: TreeItem[] = [];
  private rerenderFn: () => void;

  constructor(rerender: () => void) {
    this.rerenderFn = rerender;
  }

  setFilter(directoryPath: string | null, treeData: TreeItem[]): void {
    this.directoryFilter = directoryPath;
    this.filteredTreeData = directoryPath
      ? this.filterTreeByDirectory(treeData, directoryPath)
      : [];
    this.rerenderFn();
  }

  getFilter(): string | null {
    return this.directoryFilter;
  }
  getFilteredData(): TreeItem[] {
    return this.filteredTreeData;
  }
  isActive(): boolean {
    return this.directoryFilter !== null;
  }

  private filterTreeByDirectory(
    items: TreeItem[],
    targetDir: string,
  ): TreeItem[] {
    const result: TreeItem[] = [];
    for (const item of items) {
      if (item.path === targetDir || item.path.startsWith(targetDir + "/")) {
        result.push(item);
      } else if (
        item.type === "directory" &&
        targetDir.startsWith(item.path + "/")
      ) {
        const filteredItem: TreeItem = {
          ...item,
          children: item.children
            ? this.filterTreeByDirectory(item.children, targetDir)
            : [],
        };
        if (filteredItem.children && filteredItem.children.length > 0)
          result.push(filteredItem);
      }
    }
    return result;
  }
}
