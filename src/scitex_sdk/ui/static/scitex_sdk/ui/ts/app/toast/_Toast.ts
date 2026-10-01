/**
 * Toast — transient notification with an optional undo.
 *
 * Harvested from scitex-cards' board_v3 `toast()` / `toastUndo()`. Three
 * defects in the original are fixed here rather than carried across:
 *
 *   1. TIMERS WERE NEVER CANCELLED. Each call scheduled a bare `setTimeout`
 *      to remove the `show` class. Two messages in quick succession meant the
 *      FIRST message's timer fired while the SECOND was on screen, hiding it
 *      early — the faster the app talked, the less the user read.
 *
 *   2. `toastUndo(msg, undoFn, window)` NAMED ITS THIRD PARAMETER `window`,
 *      shadowing the global inside the function body. It worked only because
 *      nothing in the body touched the real `window`; any later line that did
 *      would have read a number instead.
 *
 *   3. IT REQUIRED A HAND-PLACED `#toast` DIV and called `.innerHTML` on the
 *      lookup without a null check, so any page missing that element threw on
 *      the first notification.
 *
 * Message text is set with `textContent`, never `innerHTML`: toasts routinely
 * carry server errors and user-supplied names, and the original's
 * `el.innerHTML = ""` sat one careless edit away from being an injection site.
 */

import type {
  ToastConfig,
  ToastOptions,
  ToastTone,
  UndoOptions,
} from "./types";

const DEFAULT_DURATION = 3600;
const DEFAULT_UNDO_DURATION = 10000;
const DEFAULT_UNDO_LABEL = "↺ Undo";

export class Toast {
  readonly el: HTMLDivElement;

  private readonly host: HTMLElement;
  private readonly duration: number;
  private readonly undoDuration: number;
  private readonly undoLabel: string;

  /** The single pending hide. Held so a new message can cancel the old one. */
  private hideTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(config: ToastConfig = {}) {
    this.host = config.host ?? document.body;
    this.duration = config.duration ?? DEFAULT_DURATION;
    this.undoDuration = config.undoDuration ?? DEFAULT_UNDO_DURATION;
    this.undoLabel = config.undoLabel ?? DEFAULT_UNDO_LABEL;

    this.el = document.createElement("div");
    this.el.className = "stx-toast";
    // A toast announces something that already happened; `status` lets a
    // screen reader speak it without stealing focus from what the user is
    // doing, which `alert` would.
    this.el.setAttribute("role", "status");
    this.el.setAttribute("aria-live", "polite");
  }

  /** Append to the host. Idempotent. */
  attach(): this {
    if (!this.el.isConnected) this.host.appendChild(this.el);
    return this;
  }

  /** Show a plain message. */
  show(message: string, options: ToastOptions = {}): this {
    this.reset(message, options.tone ?? "info");
    this.armHide(options.duration ?? this.duration);
    return this;
  }

  /**
   * Show a message with an undo button.
   *
   * The button disables itself for the duration of `onUndo`, so a slow
   * handler cannot be fired twice by an impatient click. The toast hides
   * whether the undo resolved or threw — leaving it up after a failed undo
   * would suggest the action is still reversible when it is not.
   */
  showUndo(message: string, options: UndoOptions): this {
    this.reset(message, options.tone ?? "info");

    const button = document.createElement("button");
    button.type = "button";
    button.className = "stx-toast__undo";
    button.textContent = this.undoLabel;
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        await options.onUndo();
      } catch (error) {
        options.onUndoError?.(error);
      } finally {
        this.hide();
      }
    });
    this.el.appendChild(button);

    this.armHide(options.duration ?? this.undoDuration);
    return this;
  }

  /** Hide immediately and cancel any pending auto-hide. */
  hide(): this {
    this.clearTimer();
    this.el.classList.remove("stx-toast--visible");
    return this;
  }

  /** Remove from the DOM and drop the pending timer. */
  destroy(): void {
    this.clearTimer();
    this.el.remove();
  }

  private reset(message: string, tone: ToastTone): void {
    this.attach();
    this.clearTimer();

    this.el.textContent = "";
    const span = document.createElement("span");
    span.className = "stx-toast__message";
    span.textContent = message;
    this.el.appendChild(span);

    // Set the tone as a single attribute rather than toggling one class per
    // tone: a forgotten toggle is how an error message inherits the previous
    // message's success colour.
    this.el.dataset.tone = tone;
    this.el.classList.add("stx-toast--visible");
  }

  private armHide(duration: number): void {
    this.clearTimer();
    this.hideTimer = setTimeout(() => {
      this.hideTimer = null;
      this.el.classList.remove("stx-toast--visible");
    }, duration);
  }

  private clearTimer(): void {
    if (this.hideTimer !== null) {
      clearTimeout(this.hideTimer);
      this.hideTimer = null;
    }
  }
}

/** Create and attach a toast host. */
export function createToast(config: ToastConfig = {}): Toast {
  return new Toast(config).attach();
}
