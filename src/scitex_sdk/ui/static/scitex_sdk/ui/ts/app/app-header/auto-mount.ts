/** Entry for the pre-built `js/app/app-header.js` (pages without a bundler). */

import { mountAppHeader, stxAppHeader } from "./mount";

export * from "./index";

declare global {
  interface Window {
    stxAppHeader?: typeof stxAppHeader;
  }
}

window.stxAppHeader = stxAppHeader;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountAppHeader());
} else {
  mountAppHeader();
}
