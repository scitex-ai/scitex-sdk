/**
 * Mount every `[data-stx-panes]` root and expose the `stxPanes` page API.
 *
 *   stxPanes.show("plot")               // the only panes root, or the one holding "plot"
 *   stxPanes.show("plot", "figrecipe")  // a specific app
 */

import { PANES_ATTRIBUTE, Panes } from "./_Panes";
import type { PanesOptions } from "./types";

const MOUNTED_ATTRIBUTE = "data-stx-panes-mounted";
const instances: Panes[] = [];

export function mountPanes(root: ParentNode = document, options: PanesOptions = {}): Panes[] {
  const mounted: Panes[] = [];
  for (const element of Array.from(root.querySelectorAll<HTMLElement>(`[${PANES_ATTRIBUTE}]`))) {
    if (element.hasAttribute(MOUNTED_ATTRIBUTE)) continue;
    element.setAttribute(MOUNTED_ATTRIBUTE, "");
    const panes = new Panes(element, options);
    instances.push(panes);
    mounted.push(panes);
  }
  return mounted;
}

/** The mounted panes for `app`, else the one containing `pane`, else the only one. */
export function getPanes(app?: string, pane?: string): Panes | null {
  if (app) return instances.find((item) => item.app === app) ?? null;
  if (pane) {
    const holder = instances.find((item) => item.panes.some((info) => info.id === pane));
    if (holder) return holder;
  }
  return instances.length === 1 ? instances[0] : null;
}

export function showPane(pane: string, app?: string): boolean {
  return getPanes(app, pane)?.show(pane) ?? false;
}

export const stxPanes = { mount: mountPanes, get: getPanes, show: showPane };
