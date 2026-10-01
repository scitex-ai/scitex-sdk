/**
 * AJAX Page Loader — loads pages into a container without full reload.
 *
 * Reusable component for any app that needs in-page navigation.
 * Sends X-Workspace-Shell: 1 header so Django views return partials.
 */

export { AjaxLoader } from "./_AjaxLoader";
export type { AjaxLoaderOptions } from "./types";
