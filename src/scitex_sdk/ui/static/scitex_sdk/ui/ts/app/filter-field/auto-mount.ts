import { mountFilterFields } from "./index";
export * from "./index";
// Mount immediately as well as at DOM ready: a following app module can wire
// its input listeners regardless of the document's loading phase.
mountFilterFields();
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountFilterFields(), { once: true });
}
