/** Entry for the pre-built `js/app/app-help.js` the `{% stx_help %}` tag loads. */

import { mountAppHelp, stxHelp } from "./mount";

export * from "./index";

declare global {
  interface Window {
    stxHelp?: typeof stxHelp;
  }
}

window.stxHelp = stxHelp;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountAppHelp());
} else {
  mountAppHelp();
}
