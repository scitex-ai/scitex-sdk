/** Entry for the pre-built `js/app/selector-nav.js` (pages without a bundler). */

import { mountSelectorNavs, stxSelectorNav } from "./mount";

export * from "./index";

declare global {
  interface Window {
    stxSelectorNav?: typeof stxSelectorNav;
  }
}

window.stxSelectorNav = stxSelectorNav;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountSelectorNavs());
} else {
  mountSelectorNavs();
}
