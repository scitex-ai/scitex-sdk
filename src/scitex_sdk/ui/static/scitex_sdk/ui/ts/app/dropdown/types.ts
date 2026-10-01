/**
 * Type definitions for the Dropdown component.
 */

import type { BaseComponentConfig } from "../../_base/types";

export interface DropdownItem {
  id: string;
  label: string;
  icon?: string;
  disabled?: boolean;
  separator?: boolean;
  onClick?: () => void;
}

export interface DropdownConfig extends BaseComponentConfig {
  /** Menu items */
  items: DropdownItem[];
  /** Trigger element (button that opens the dropdown) */
  trigger: string | HTMLElement;
  /** Alignment relative to trigger: "left" or "right" (default: "left") */
  align?: "left" | "right";
  /** Called when an item is selected */
  onSelect?: (item: DropdownItem) => void;

  /**
   * Show a fuzzy-filter input above the items.
   *
   * Left unset it is AUTOMATIC: the filter appears once the list exceeds
   * `filterThreshold`. That default is the point of this option — a long
   * unfiltered picker is a UX defect, and requiring every caller to remember
   * an opt-in flag guarantees some of them will not. Set `false` to suppress
   * it (a deliberately short action menu), `true` to force it.
   */
  filter?: boolean;

  /**
   * Item count above which the filter appears automatically. Default 8 —
   * roughly where scanning a list stops being faster than typing.
   * Separators do not count toward it.
   */
  filterThreshold?: number;

  /** Placeholder for the filter input. */
  filterPlaceholder?: string;

  /** Text shown when the query matches nothing. Defaults to "No matches". */
  emptyText?: string;
}
