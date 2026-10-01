/**
 * Mount pickers rendered by the `{% scitex_project_picker %}` template tag.
 *
 * The tag emits `<div data-stx-project-picker data-provider-url=...>`; this
 * turns each into a ProjectSelector backed by the HTTP provider. With
 * `data-navigate="?project={id}"` a pick navigates, so the page reloads with
 * an explicit project in the URL, which always wins over the stored default.
 */

import { ProjectSelector, PROJECT_SELECTOR_CHANGE } from "./_ProjectSelector";
import { httpProjectProvider } from "./provider";

export const PROJECT_PICKER_ATTRIBUTE = "data-stx-project-picker";
const MOUNTED_ATTRIBUTE = "data-stx-project-picker-mounted";

/** The URL a pick navigates to, or null when the element does not navigate. */
export function projectNavigationUrl(template: string | null, id: string): string | null {
  if (!template) return null;
  return template.split("{id}").join(encodeURIComponent(id));
}

export function mountProjectPickers(root: ParentNode = document): ProjectSelector[] {
  const mounted: ProjectSelector[] = [];
  const elements = root.querySelectorAll<HTMLElement>(`[${PROJECT_PICKER_ATTRIBUTE}]`);
  for (const element of Array.from(elements)) {
    if (element.hasAttribute(MOUNTED_ATTRIBUTE)) continue;
    const providerUrl = element.getAttribute("data-provider-url");
    if (!providerUrl) continue;
    element.setAttribute(MOUNTED_ATTRIBUTE, "");

    const selector = new ProjectSelector({
      container: element,
      provider: httpProjectProvider(providerUrl),
      current: element.getAttribute("data-current") || null,
      placeholder: element.getAttribute("data-placeholder") || undefined,
    });
    const navigate = element.getAttribute("data-navigate");
    element.addEventListener(PROJECT_SELECTOR_CHANGE, (event) => {
      const { id } = (event as CustomEvent<{ id: string }>).detail;
      const url = projectNavigationUrl(navigate, id);
      if (url) window.location.assign(url);
    });
    mounted.push(selector);
  }
  return mounted;
}
