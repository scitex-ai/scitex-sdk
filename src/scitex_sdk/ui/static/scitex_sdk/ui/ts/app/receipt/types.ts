/**
 * Delivery receipt — public types.
 */

/**
 * The four delivery states.
 *
 * `unknown` is a FIRST-CLASS state, not the absence of one. A boolean
 * read/unread cannot express "no signal yet", and collapsing that into either
 * pole — showing an undelivered message as sent, or a delivered one as not —
 * is the failure this type exists to prevent.
 */
export type ReceiptState = "unknown" | "sent" | "seen" | "failed";

export const RECEIPT_STATES: readonly ReceiptState[] = [
  "unknown",
  "sent",
  "seen",
  "failed",
] as const;

/** Glyph shown for each state. Override per app; emoji vs icon font is yours. */
export interface ReceiptGlyphs {
  unknown: string;
  sent: string;
  seen: string;
  failed: string;
}

/** Accessible description for each state, used as title + aria-label. */
export interface ReceiptLabels {
  unknown: string;
  sent: string;
  seen: string;
  failed: string;
}

export interface ReceiptConfig {
  /**
   * Starting state. Defaults to `unknown` ON PURPOSE — a receipt you forgot to
   * update must never read as delivered, so claiming delivery is opt-in.
   */
  state?: ReceiptState;
  glyphs?: Partial<ReceiptGlyphs>;
  labels?: Partial<ReceiptLabels>;
}
