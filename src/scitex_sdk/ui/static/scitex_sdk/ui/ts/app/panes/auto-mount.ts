/** Entry for the pre-built `js/app/panes.js` the `{% scitex_panes %}` tag loads. */

import { mountPanes, stxPanes } from "./mount";

export * from "./index";

declare global {
  interface Window {
    stxPanes?: typeof stxPanes;
  }
}

window.stxPanes = stxPanes;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountPanes());
} else {
  mountPanes();
}
