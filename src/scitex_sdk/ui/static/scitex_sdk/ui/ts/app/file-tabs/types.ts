/**
 * Type definitions for the FileTabs component.
 */

import type { BaseComponentConfig } from "../../_base/types";

export interface FileTab {
  path: string;
  label?: string;
  isDirty?: boolean;
  isPermanent?: boolean;
}

export interface FileTabsConfig extends BaseComponentConfig {
  /** Called when user switches to a tab */
  onTabSwitch: (path: string) => void;
  /** Called when user closes a tab */
  onTabClose: (path: string) => void;
  /** Called when user creates a new file via + button */
  onNewFile?: (name: string) => void;
  /** Called on double-click rename */
  onRename?: (oldPath: string, newPath: string) => void;
  /** Show + button for new files (default: true) */
  showNewButton?: boolean;
  /** Allow drag-and-drop reordering (default: true) */
  allowReorder?: boolean;
  /** Tab path that cannot be closed */
  permanentTab?: string;
}
