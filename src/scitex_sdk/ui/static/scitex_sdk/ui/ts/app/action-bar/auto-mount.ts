/** Entry for the pre-built `js/app/action-bar.js`, for pages with no bundler. */

import { mountActionBar, stxActionBar } from "./mount";

export * from "./index";

declare global {
  interface Window {
    stxActionBar?: typeof stxActionBar;
  }
}

window.stxActionBar = stxActionBar;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountActionBar());
} else {
  mountActionBar();
}
