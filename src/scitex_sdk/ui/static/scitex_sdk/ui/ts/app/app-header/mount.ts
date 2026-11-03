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
const instances: { header: AppHeader; container: HTMLElement }[] = [];

export function mountAppHeader(
  root: ParentNode = document,
  options: Partial<AppHeaderConfig> = {},
): AppHeader[] {
  // The host can replace an owned module region without reloading the page.
  // Dispose only detached SDK instances; connected headers keep their identity.
  for (let i = instances.length - 1; i >= 0; i--) {
    const previous = instances[i];
    if (!previous.header.headerEl.isConnected) {
      // A detached header does not authorize erasing a still-connected region
      // that its owner may have repurposed. Dispose only detached containers.
      if (!previous.container.isConnected) previous.header.destroy();
      instances.splice(i, 1);
    }
  }
  const declared = root.querySelectorAll(`[${HEADER_ATTRIBUTE}]`);
  const regionPickers = root instanceof Element && declared.length === 1
    ? root.querySelectorAll<HTMLElement>(".stx-app-project-selector[data-stx-project-picker]")
    : null;
  const mounted: AppHeader[] = [];
  for (const element of Array.from(
    root.querySelectorAll<HTMLElement>(`[${HEADER_ATTRIBUTE}]`),
  )) {
    if (element.hasAttribute(MOUNTED_ATTRIBUTE)) continue;
    element.setAttribute(MOUNTED_ATTRIBUTE, "");
    const header = new AppHeader({ ...options, container: element });
    // Django renders the SDK picker before this module mounts the header.
    // Adopt that same node immediately, rather than leaving a second row until
    // a leaf's (potentially much larger) viewer module finishes loading.
    // Only direct SDK controls belong here; scripts, catalogs and embedded
    // surfaces stay in their original containers.
    const pickers = element.querySelectorAll<HTMLElement>(
      ":scope > .stx-app-project-selector[data-stx-project-picker]",
    );
    // An explicitly supplied element is a host-owned module region, unlike
    // document-wide auto-mount. It may declare one sibling picker for one
    // header; multiple candidates remain untouched rather than guessed.
    const picker = pickers.length === 1 ? pickers[0]
      : pickers.length === 0 && regionPickers?.length === 1 ? regionPickers[0] : null;
    if (header.projectSlot && picker) header.projectSlot.appendChild(picker);
    instances.push({ header, container: element });
    mounted.push(header);
  }
  return mounted;
}

/** The only mounted header, or `null` when there is not exactly one. */
export function getAppHeader(): AppHeader | null {
  const connected = instances.filter(({ header }) => header.headerEl.isConnected);
  return connected.length === 1 ? connected[0].header : null;
}

export const stxAppHeader = {
  mount: mountAppHeader,
  get: getAppHeader,
};
