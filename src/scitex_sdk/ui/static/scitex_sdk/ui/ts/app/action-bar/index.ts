/**
 * Bottom action bar — the phone action bar, once.
 *
 *   import { mountActionBar } from "scitex-ui/ts/app/action-bar";
 *
 *   // the page declares the bar, the primitive reserves its height for you
 *   mountActionBar();
 *
 *   // or name the scroller the height must be reserved on
 *   mountActionBar(document, { reserveOn: document.querySelector(".editor-body") });
 *
 * Markup (any of these hooks work; the attribute is the whole contract):
 *
 *   <div class="editor-body">            <!-- the scroller -->
 *     …content…
 *   </div>
 *   <div data-stx-action-bar>
 *     <button data-stx-action-bar-item>Compile</button>
 *     <button data-stx-action-bar-item>Preview</button>
 *   </div>
 *
 * WHAT YOU STILL OWN, and it is one line: put `stx-action-bar-space` on the
 * scroller (see css/app/action-bar.css). The bar is out of flow, so the
 * container must reserve its measured height — the primitive publishes it as
 * `--stx-action-bar-height` and the utility consumes it.
 *
 * Styling: `css/app/action-bar.css`, paired with `css/shell/theme.css` for the
 * tokens. No shell adoption required.
 */

export { ActionBar, BAR_ATTRIBUTE, HEIGHT_PROPERTY, ITEM_ATTRIBUTE, MOUNTED_ATTRIBUTE } from "./_ActionBar";
export { actionBarHeight, getActionBar, mountActionBar, stxActionBar } from "./mount";
export { ACTION_BAR_CHANGE } from "./types";
export type { ActionBarChangeDetail, ActionBarOptions } from "./types";
