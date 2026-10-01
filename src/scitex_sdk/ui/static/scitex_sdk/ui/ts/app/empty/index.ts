/**
 * Empty state — the "nothing here" block, once.
 *
 *   import { renderEmptyState } from "scitex-ui/ts/app/empty";
 *
 *   pane.appendChild(renderEmptyState({
 *     iconClass: "fas fa-inbox",
 *     title: "No cards match this filter",
 *     hint: "Clear the filter or widen the date range",
 *   }));
 *
 *   // inline, for a dropdown or a narrow pane
 *   list.appendChild(renderEmptyState({ title: "No results", compact: true }));
 *
 * Styling: `css/app/empty.css`, paired with `css/shell/theme.css` for the
 * tokens. No shell adoption required.
 */

export { renderEmptyState } from "./_EmptyState";
export type { EmptyStateConfig } from "./types";
