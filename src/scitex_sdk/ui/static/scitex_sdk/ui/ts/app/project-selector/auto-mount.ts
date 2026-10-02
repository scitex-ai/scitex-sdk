/** Entry for the canonical pre-built `js/app/project-selector.js`. */

import { mountProjectPickers } from "./mount";
export * from "./index";

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => mountProjectPickers());
  } else {
    mountProjectPickers();
  }
}
