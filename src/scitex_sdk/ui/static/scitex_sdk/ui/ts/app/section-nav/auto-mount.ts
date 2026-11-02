import { mountSectionNavs } from "./index";
export * from "./index";
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountSectionNavs(), { once: true });
} else mountSectionNavs();
