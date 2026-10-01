// src/scitex_ui/static/scitex_ui/ts/app/toast/_Toast.ts
var DEFAULT_DURATION = 3600;
var DEFAULT_UNDO_DURATION = 1e4;
var DEFAULT_UNDO_LABEL = "\u21BA Undo";
var Toast = class {
  el;
  host;
  duration;
  undoDuration;
  undoLabel;
  /** The single pending hide. Held so a new message can cancel the old one. */
  hideTimer = null;
  constructor(config = {}) {
    this.host = config.host ?? document.body;
    this.duration = config.duration ?? DEFAULT_DURATION;
    this.undoDuration = config.undoDuration ?? DEFAULT_UNDO_DURATION;
    this.undoLabel = config.undoLabel ?? DEFAULT_UNDO_LABEL;
    this.el = document.createElement("div");
    this.el.className = "stx-toast";
    this.el.setAttribute("role", "status");
    this.el.setAttribute("aria-live", "polite");
  }
  /** Append to the host. Idempotent. */
  attach() {
    if (!this.el.isConnected) this.host.appendChild(this.el);
    return this;
  }
  /** Show a plain message. */
  show(message, options = {}) {
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
  showUndo(message, options) {
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
  hide() {
    this.clearTimer();
    this.el.classList.remove("stx-toast--visible");
    return this;
  }
  /** Remove from the DOM and drop the pending timer. */
  destroy() {
    this.clearTimer();
    this.el.remove();
  }
  reset(message, tone) {
    this.attach();
    this.clearTimer();
    this.el.textContent = "";
    const span = document.createElement("span");
    span.className = "stx-toast__message";
    span.textContent = message;
    this.el.appendChild(span);
    this.el.dataset.tone = tone;
    this.el.classList.add("stx-toast--visible");
  }
  armHide(duration) {
    this.clearTimer();
    this.hideTimer = setTimeout(() => {
      this.hideTimer = null;
      this.el.classList.remove("stx-toast--visible");
    }, duration);
  }
  clearTimer() {
    if (this.hideTimer !== null) {
      clearTimeout(this.hideTimer);
      this.hideTimer = null;
    }
  }
};
function createToast(config = {}) {
  return new Toast(config).attach();
}

// src/scitex_ui/static/scitex_ui/ts/app/toast/types.ts
var TOAST_TONES = [
  "info",
  "success",
  "error"
];
export {
  TOAST_TONES,
  Toast,
  createToast
};
