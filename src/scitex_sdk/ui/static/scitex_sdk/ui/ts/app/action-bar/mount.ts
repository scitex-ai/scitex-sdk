/**
 * Mount every `[data-stx-action-bar]` element and expose the `stxActionBar`
 * page API.
 *
 *   stxActionBar.mount()     // mount everything declared in the page
 *   stxActionBar.get()       // the mounted bar (the last one), or null
 *   stxActionBar.height()    // its last measured height in CSS pixels
 */

import { ActionBar, BAR_ATTRIBUTE, MOUNTED_ATTRIBUTE } from "./_ActionBar";
import type { ActionBarOptions } from "./types";

const instances: ActionBar[] = [];

export function mountActionBar(
  root: ParentNode = document,
  options: ActionBarOptions = {},
): ActionBar[] {
  const mounted: ActionBar[] = [];
  for (const element of Array.from(
    root.querySelectorAll<HTMLElement>(`[${BAR_ATTRIBUTE}]`),
  )) {
    if (element.hasAttribute(MOUNTED_ATTRIBUTE)) continue;
    element.setAttribute(MOUNTED_ATTRIBUTE, "");
    const bar = new ActionBar(element, options);
    instances.push(bar);
    mounted.push(bar);
  }
  return mounted;
}

/** The most recently mounted bar, or null. */
export function getActionBar(): ActionBar | null {
  return instances.length > 0 ? instances[instances.length - 1] : null;
}

/** The mounted bar's last measured height, or 0. */
export function actionBarHeight(): number {
  return getActionBar()?.height ?? 0;
}

export const stxActionBar = {
  mount: mountActionBar,
  get: getActionBar,
  height: actionBarHeight,
};
