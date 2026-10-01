/**
 * Mount every `[data-stx-help]` root and expose the `stxHelp` page API.
 *
 *   stxHelp.open()            // the only help root, or the one for `app`
 *   stxHelp.open("scholar")   // a specific app
 *   stxHelp.close()
 *   stxHelp.replay()          // replay the tour
 */

import { AppHelp, HELP_ATTRIBUTE } from "./_AppHelp";
import type { AppHelpOptions } from "./types";

const MOUNTED_ATTRIBUTE = "data-stx-help-mounted";
const instances: AppHelp[] = [];

export function mountAppHelp(root: ParentNode = document, options: AppHelpOptions = {}): AppHelp[] {
  const mounted: AppHelp[] = [];
  for (const element of Array.from(root.querySelectorAll<HTMLElement>(`[${HELP_ATTRIBUTE}]`))) {
    if (element.hasAttribute(MOUNTED_ATTRIBUTE)) continue;
    element.setAttribute(MOUNTED_ATTRIBUTE, "");
    const help = new AppHelp(element, options);
    instances.push(help);
    mounted.push(help);
  }
  return mounted;
}

/** The mounted help for `app`, else the only one. */
export function getAppHelp(app?: string): AppHelp | null {
  if (app) return instances.find((item) => item.app === app) ?? null;
  return instances.length === 1 ? instances[0] : null;
}

export function openHelp(app?: string): void {
  getAppHelp(app)?.openPanel();
}

export function closeHelp(app?: string): void {
  getAppHelp(app)?.closePanel();
}

export function replayHelp(app?: string): void {
  getAppHelp(app)?.replayTour();
}

export const stxHelp = {
  mount: mountAppHelp,
  get: getAppHelp,
  open: openHelp,
  close: closeHelp,
  replay: replayHelp,
};
