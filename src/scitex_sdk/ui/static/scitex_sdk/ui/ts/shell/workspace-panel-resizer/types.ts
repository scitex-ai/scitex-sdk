/** Panel configuration for WorkspacePanelResizer */
export interface PanelConfig {
  /** ID of the resizer element */
  resizerId: string;
  /** CSS selector for the panel to resize */
  targetPanel: string;
  /** Minimum size in pixels (collapsed state size) — used as minWidth or minHeight depending on axis */
  minWidth: number;
  /** localStorage key for saved size */
  storageKey: string;
  /** Direction: 'left'/'right' (horizontal) or 'top'/'bottom' (vertical, auto-mapped) */
  resizeDirection: "left" | "right";
  /** Optional: ID of toggle button to sync icon state */
  toggleButtonId?: string;
  /** Optional: localStorage key for collapse state */
  collapseStorageKey?: string;
  /** Optional: Default size when not collapsed */
  defaultWidth?: number;
  /** Optional: Panel size is fixed — resizer only propagates to adjacent panels */
  fixedWidth?: boolean;
}
