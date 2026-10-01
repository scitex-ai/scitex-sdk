/**
 * Toast — public types.
 */

/**
 * Toast severity. `success` and `error` are the two the harvested source
 * distinguished; `info` exists so a neutral message does not have to lie in
 * one direction or the other.
 */
export type ToastTone = "info" | "success" | "error";

export const TOAST_TONES: readonly ToastTone[] = [
  "info",
  "success",
  "error",
] as const;

export interface ToastConfig {
  /**
   * Host element the toast is appended to. Defaults to `document.body`.
   *
   * The harvested original looked up a hard-coded `#toast` element and called
   * `.innerHTML` on the result without checking it existed, so a page that had
   * not hand-placed that div crashed on the first notification. Owning the
   * element removes that precondition entirely.
   */
  host?: HTMLElement;

  /** Milliseconds before an ordinary toast auto-hides. */
  duration?: number;

  /**
   * Milliseconds an undo toast stays actionable. Longer than `duration` on
   * purpose: an undo the user cannot reach in time is decoration.
   */
  undoDuration?: number;

  /** Label for the undo button. */
  undoLabel?: string;
}

export interface ToastOptions {
  tone?: ToastTone;
  /** Override the auto-hide delay for this one message. */
  duration?: number;
}

export interface UndoOptions extends ToastOptions {
  /**
   * Called when the user clicks undo. May be async; the toast stays visible
   * with the button disabled until it settles, so a slow undo cannot be
   * double-fired, and it hides whether the undo resolved or threw.
   */
  onUndo: () => void | Promise<void>;
  /** Called if `onUndo` rejects, so the caller can surface the failure. */
  onUndoError?: (error: unknown) => void;
}
