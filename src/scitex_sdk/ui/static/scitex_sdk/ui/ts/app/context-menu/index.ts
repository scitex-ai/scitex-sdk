/**
 * Context menu — right-click menu with positioning, dismissal and keyboard nav.
 *
 *   import { initContextMenu } from "scitex-ui/ts/app/context-menu";
 *
 *   initContextMenu({
 *     target: "#messages",
 *     items: (el) => [
 *       { kind: "label", label: "Message" },
 *       { label: "Reply", icon: "fas fa-reply", shortcut: "Ctrl+R",
 *         onSelect: () => reply(el) },
 *       { label: "Copy", icon: "fas fa-copy", onSelect: () => copy(el) },
 *       { kind: "divider" },
 *       { label: "Delete", icon: "fas fa-trash", danger: true,
 *         onSelect: () => remove(el) },
 *     ],
 *   });
 *
 * Styling ships separately and needs no shell adoption — link
 * `css/shell/theme.css` (tokens) and `css/app/context-menu.css`.
 */

export { ContextMenu, initContextMenu } from "./_ContextMenu";
export type {
  ContextMenuConfig,
  ContextMenuEntry,
  ContextMenuItem,
  ContextMenuDivider,
  ContextMenuLabel,
} from "./types";
