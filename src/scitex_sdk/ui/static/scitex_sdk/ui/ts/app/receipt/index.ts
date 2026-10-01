/**
 * Delivery receipt — one mark that advances through its delivery states.
 *
 *   import { renderReceipt } from "scitex-ui/ts/app/receipt";
 *
 *   const receipt = renderReceipt();          // starts at "unknown"
 *   row.appendChild(receipt.el);
 *   receipt.set("sent");                      // reached the store
 *   receipt.set("seen");                      // reached the recipient
 *   receipt.set("failed");                    // known-dead delivery
 *
 * Styling: `css/app/receipt.css` (no shell adoption required — pair it with
 * `css/shell/theme.css` for the tokens).
 */

export { Receipt, renderReceipt } from "./_Receipt";
export { RECEIPT_STATES } from "./types";
export type {
  ReceiptConfig,
  ReceiptGlyphs,
  ReceiptLabels,
  ReceiptState,
} from "./types";
