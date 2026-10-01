/**
 * Mount every `[data-stx-selector-nav]` root and expose the `stxSelectorNav`
 * page API — the no-bundler path.
 *
 *   stxSelectorNav.mount()          // auto-mounts every declared root
 *   stxSelectorNav.get()            // the only mounted instance, or null
 *   stxSelectorNav.select("page-2") // select an id on the only instance
 */

import { SelectorNav } from "./_SelectorNav";
import { SELECTOR_NAV_ATTRIBUTE } from "./types";
import type { SelectorNavConfig, SelectorNavItem } from "./types";

const MOUNTED_ATTRIBUTE = "data-stx-selector-nav-mounted";
const instances: SelectorNav[] = [];

/** The tree a root declares, from its `data-stx-items` JSON (or an empty tree). */
function readItems(element: HTMLElement): SelectorNavItem[] {
  const raw = element.getAttribute("data-stx-items");
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as SelectorNavItem[];
    if (!Array.isArray(parsed)) throw new TypeError("not an array of nodes");
    return parsed;
  } catch (error) {
    // Refused loudly, same rule as the header payload: a selector that renders
    // an EMPTY strip looks exactly like an app with one section.
    throw new Error(
      `SelectorNav: ${SELECTOR_NAV_ATTRIBUTE} carries an unreadable ` +
        `data-stx-items payload (${(error as Error).message}). Refusing to ` +
        "render a selector with no sections.",
    );
  }
}

export function mountSelectorNavs(
  root: ParentNode = document,
  options: Partial<SelectorNavConfig> = {},
): SelectorNav[] {
  const mounted: SelectorNav[] = [];
  for (const element of Array.from(
    root.querySelectorAll<HTMLElement>(`[${SELECTOR_NAV_ATTRIBUTE}]`),
  )) {
    if (element.hasAttribute(MOUNTED_ATTRIBUTE)) continue;
    element.setAttribute(MOUNTED_ATTRIBUTE, "");
    const nav = new SelectorNav({
      ...options,
      container: element,
      items: options.items ?? readItems(element),
      current: options.current ?? element.getAttribute("data-stx-current"),
    });
    instances.push(nav);
    mounted.push(nav);
  }
  return mounted;
}

export function getSelectorNav(): SelectorNav | null {
  return instances.length === 1 ? instances[0] : null;
}

export function selectSelectorNav(id: string): void {
  getSelectorNav()?.setCurrent(id);
}

export const stxSelectorNav = {
  mount: mountSelectorNavs,
  get: getSelectorNav,
  select: selectSelectorNav,
};
