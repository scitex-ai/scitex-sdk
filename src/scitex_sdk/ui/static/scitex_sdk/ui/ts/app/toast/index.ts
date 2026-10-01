/**
 * Toast — transient notification, optionally undoable.
 *
 *   import { createToast } from "scitex-ui/ts/app/toast";
 *
 *   const toast = createToast();
 *   toast.show("Saved");
 *   toast.show("Could not save", { tone: "error" });
 *
 *   toast.showUndo("Card deleted", {
 *     onUndo: () => restore(card),
 *     onUndoError: (e) => toast.show(String(e), { tone: "error" }),
 *   });
 *
 * One instance owns one on-screen slot: a second message replaces the first
 * and cancels its pending hide. Create separate instances with distinct
 * `host` elements if you need more than one slot.
 *
 * Styling: `css/app/toast.css` (pair with `css/shell/theme.css` for tokens).
 */

export { Toast, createToast } from "./_Toast";
export { TOAST_TONES } from "./types";
export type {
  ToastConfig,
  ToastOptions,
  ToastTone,
  UndoOptions,
} from "./types";
