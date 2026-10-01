/**
 * Reply quote — a truncated, clickable quote of the message being replied to.
 *
 *   import { renderReplyQuote } from "scitex-ui/ts/app/reply-quote";
 *
 *   const quote = renderReplyQuote({
 *     author: "operator",
 *     text: "can you check the board on mobile?",
 *     targetId: "msg-1481",
 *   });
 *   bubble.prepend(quote.el);
 *
 * Colours are inherited from the surrounding bubble via `currentColor`, so it
 * works inside sender-coloured bubbles with no per-sender configuration.
 * A quote whose original cannot be found renders visibly orphaned rather than
 * staying clickable and doing nothing.
 *
 * Styling: `css/app/reply-quote.css` — pair with `css/shell/theme.css` for
 * the tokens; no shell adoption required.
 */

export { ReplyQuote, renderReplyQuote } from "./_ReplyQuote";
export type { ReplyQuoteConfig } from "./types";
