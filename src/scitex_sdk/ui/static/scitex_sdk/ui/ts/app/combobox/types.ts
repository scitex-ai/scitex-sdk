/**
 * Type definitions for the Combobox component.
 *
 * The Combobox is a fuzzy-typeahead select: a trigger button opens a
 * popover containing a search input and a filtered list of options.
 * It generalises a plain <select> to the case where the option list is
 * long enough to benefit from substring search, and optionally allows
 * the user to create a new value on the fly (the `onCreate` callback).
 */

import type { BaseComponentConfig } from "../../_base/types";

export interface ComboboxItem {
  /** Stable identifier for the option (passed back via onChange). */
  value: string;
  /** Display label (what the user sees in the list). */
  label: string;
  /** Optional grouping header — adjacent items with the same `group`
   *  are rendered under one section header. */
  group?: string;
  /** Disable selection of this item. */
  disabled?: boolean;
}

export interface ComboboxConfig extends BaseComponentConfig {
  /** Trigger element (button that opens the combobox). The visible
   *  label of the trigger is updated to the selected item's label
   *  unless `updateTriggerLabel: false` is set. */
  trigger: string | HTMLElement;
  /** Options to show in the filtered list. May be updated dynamically
   *  via `setItems`. */
  items: ComboboxItem[];
  /** Pre-selected value (matched by `ComboboxItem.value`). */
  value?: string;
  /** Placeholder shown in the search input. */
  placeholder?: string;
  /** Alignment relative to trigger. Defaults to "left". */
  align?: "left" | "right";
  /** Fuzzy mode (subsequence match, default true) or strict prefix
   *  match (false). Fuzzy mirrors the same algorithm used in fzf /
   *  scitex-todo's existing fuzzy-search. */
  fuzzy?: boolean;
  /** Optional empty-state text rendered when no item matches. Defaults
   *  to "No matches". */
  emptyText?: string;
  /** Optional label shown next to the create-new affordance. Defaults
   *  to "+ Create <query>" — see `onCreate`. If `onCreate` is unset,
   *  the create affordance is hidden. */
  createLabel?: (rawQuery: string) => string;
  /** Whether to replace the trigger's text content with the selected
   *  label after onChange. Defaults to true. */
  updateTriggerLabel?: boolean;
  /** Fired when the user picks an item via mouse or keyboard. */
  onChange?: (item: ComboboxItem) => void;
  /** Optional — when present a "+ Create '<query>'" row appears at the
   *  bottom of the list whenever the query does not exactly match an
   *  existing item's label. Selecting it calls onCreate(rawQuery)
   *  instead of onChange. The consumer is responsible for creating the
   *  new item (e.g. POST to a backend) and then calling
   *  `combobox.setItems(...)` to include it. */
  onCreate?: (rawQuery: string) => void;
}
