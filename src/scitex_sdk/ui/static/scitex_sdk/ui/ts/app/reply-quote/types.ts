/**
 * Reply quote — public types.
 */

export interface ReplyQuoteConfig {
  /** Display name of whoever wrote the quoted message. */
  author: string;
  /** The quoted body. Truncated to two lines by CSS, never by this module. */
  text: string;
  /**
   * `id` of the original message element. When it resolves, activating the
   * quote scrolls to it and flashes it. When it does NOT resolve, the quote
   * renders ORPHANED — visibly inert — rather than staying clickable and
   * doing nothing.
   */
  targetId?: string;
  /**
   * Called instead of the built-in scroll. Use when the original may be
   * outside the DOM — a windowed list, or a page that must be loaded first.
   * Return `true` if you handled it; `false` renders the quote orphaned.
   */
  onActivate?: (targetId: string | undefined) => boolean;
  /** Milliseconds the original stays highlighted after a jump. Default 1200. */
  flashMs?: number;
}
