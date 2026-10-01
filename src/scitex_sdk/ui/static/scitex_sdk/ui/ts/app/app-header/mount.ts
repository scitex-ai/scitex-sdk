/**
 * Mount every `[data-stx-app-header]` root and expose the `stxAppHeader` page API.
 *
 *   stxAppHeader.mount()      // auto-mounts every declared root
 *   stxAppHeader.get()        // the only mounted header, or null
 */

import { AppHeader } from "./_AppHeader";
import { HEADER_ATTRIBUTE } from "./types";
import type { AppHeaderConfig } from "./types";

const MOUNTED_ATTRIBUTE = "data-stx-app-header-mounted";
const instances: AppHeader[] = [];

export function mountAppHeader(
  root: ParentNode = document,
  options: Partial<AppHeaderConfig> = {},
): AppHeader[] {
  const mounted: AppHeader[] = [];
  for (const element of Array.from(
    root.querySelectorAll<HTMLElement>(`[${HEADER_ATTRIBUTE}]`),
  )) {
    if (element.hasAttribute(MOUNTED_ATTRIBUTE)) continue;
    element.setAttribute(MOUNTED_ATTRIBUTE, "");
    const header = new AppHeader({ ...options, container: element });
    instances.push(header);
    mounted.push(header);
  }
  return mounted;
}

/** The only mounted header, or `null` when there is not exactly one. */
export function getAppHeader(): AppHeader | null {
  return instances.length === 1 ? instances[0] : null;
}

export const stxAppHeader = {
  mount: mountAppHeader,
  get: getAppHeader,
};
