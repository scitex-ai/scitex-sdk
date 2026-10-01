/** Entry for the pre-built `js/app/project-picker.js` the template tag loads. */

import { mountProjectPickers } from "./mount";

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountProjectPickers());
} else {
  mountProjectPickers();
}
