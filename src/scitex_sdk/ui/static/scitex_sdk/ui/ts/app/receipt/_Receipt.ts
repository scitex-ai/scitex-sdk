/**
 * Receipt — a single delivery mark that advances through its states.
 *
 * Built base-first at scitex-cards' request so the chat never grows a private
 * one: they needed reached-the-store then reached-the-agent, modelled on
 * claude-code-telegrammer, which advances ONE mark rather than showing a row.
 *
 * The design constraint they asked for, and the reason this is not a boolean:
 * a fourth state must exist for "delivery is known to have failed", and a
 * default state must exist for "we have no signal yet" — even though their
 * first version will only ever set two of the four. A read/unread flag that
 * cannot say `unknown` silently reports undelivered messages as delivered.
 */

import type { ReceiptConfig, ReceiptGlyphs, ReceiptLabels, ReceiptState } from "./types";
import { RECEIPT_STATES } from "./types";

const DEFAULT_GLYPHS: ReceiptGlyphs = {
  unknown: "·",
  sent: "⚡",
  seen: "👀",
  failed: "⚠",
};

const DEFAULT_LABELS: ReceiptLabels = {
  unknown: "Delivery status unknown",
  sent: "Delivered to the store",
  seen: "Seen by the recipient",
  failed: "Delivery failed",
};

export class Receipt {
  readonly el: HTMLElement;
  private current: ReceiptState;
  private readonly glyphs: ReceiptGlyphs;
  private readonly labels: ReceiptLabels;

  constructor(config: ReceiptConfig = {}) {
    this.glyphs = { ...DEFAULT_GLYPHS, ...config.glyphs };
    this.labels = { ...DEFAULT_LABELS, ...config.labels };
    this.current = config.state ?? "unknown";
    assertState(this.current);

    this.el = document.createElement("span");
    this.el.className = "stx-app-receipt";
    // Announced rather than decorative: the mark carries the only delivery
    // signal in the row, so a screen reader must not skip it.
    this.el.setAttribute("role", "img");
    this.paint();
  }

  /** The state as last set. Never inferred, never guessed. */
  get state(): ReceiptState {
    return this.current;
  }

  /**
   * Move to a state. Throws on anything outside the four — an unrecognised
   * status must fail loudly here rather than silently render as `unknown`,
   * which would be indistinguishable from "no signal yet".
   */
  set(state: ReceiptState): void {
    assertState(state);
    this.current = state;
    this.paint();
  }

  private paint(): void {
    for (const s of RECEIPT_STATES) {
      this.el.classList.toggle(`stx-app-receipt--${s}`, s === this.current);
    }
    this.el.textContent = this.glyphs[this.current];
    this.el.title = this.labels[this.current];
    this.el.setAttribute("aria-label", this.labels[this.current]);
    this.el.dataset.state = this.current;
  }
}

function assertState(state: string): asserts state is ReceiptState {
  if (!(RECEIPT_STATES as readonly string[]).includes(state)) {
    throw new Error(
      `[receipt] unknown state ${JSON.stringify(state)}; expected one of ` +
        `${RECEIPT_STATES.join(", ")}. Rendering it as "unknown" would hide a ` +
        `delivery failure behind a state that means "no signal yet".`,
    );
  }
}

/** Convenience: build a receipt element in one call. */
export function renderReceipt(config: ReceiptConfig = {}): Receipt {
  return new Receipt(config);
}
