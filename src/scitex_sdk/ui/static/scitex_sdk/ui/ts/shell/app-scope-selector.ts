/**
 * app-scope-selector — the CONSUMER half of the stx-app-scope contract.
 *
 * The producer (scitex-app SDK, PR #185 @ d8528de4) stamps a project-scoped
 * app's page with `<meta name="stx-app-scope" content="project">`; user-scoped
 * pages get no marker. This module reads that marker and offers the ONE
 * project-selector behavior the ruling allows:
 *
 *   - user-scoped / no marker   -> renders NOTHING. A container given to
 *                                  mountProjectSelectorByScope() is left
 *                                  byte-for-byte empty, so "renders without a
 *                                  project switcher" is structural, not a
 *                                  convention the caller has to remember.
 *   - project-scoped            -> mounts the EXISTING scitex-ui
 *                                  ProjectSelector (../app/project-selector)
 *                                  app-locally, into the container the CALLER
 *                                  chooses — i.e. on the workspace surface,
 *                                  never in the global Hub header.
 *
 * The data (the app's own project list + active id) is always the caller's:
 * this module owns only the scope GATE and the wiring. It does NOT fork
 * ProjectSelector and it does NOT invent a new selector — the directive is to
 * reuse the existing primitive, and a second, look-alike picker is exactly the
 * leaf-local duplication the shared-SDK principle (compass L18) exists to stop.
 *
 * WHY THE GLOBAL HEADER IS OUT OF SCOPE BY CONSTRUCTION: this function takes a
 * container, so it can only ever write where it is told to. The no-header-
 * switcher ruling (compass-impl-project-files-gitux / the 2026-09-10 operator
 * decision) is enforced by simply never calling this with a header container —
 * and by the tests, which assert the marker is read from the document, not
 * that any header element is produced.
 */

import {
  ProjectSelector,
  PROJECT_SELECTOR_CHANGE,
  hostProjectProvider,
  projectNavigationUrl,
} from "../app/project-selector";
import type { ProjectOption, ProjectProvider } from "../app/project-selector";
import {
  appScope,
  SCOPE_PROJECT,
} from "../_base/scope";
import type { AppScope } from "../_base/scope";

export interface AppScopeSelectorOptions {
  /** The container to mount into. Caller-supplied, so the caller decides the
   *  surface (workspace, not the global header). */
  container: string | HTMLElement;
  /** The app's projects, in display order. The DATA is the app's — it knows
   *  its own list and permissions; this module only gates on scope. */
  projects?: ProjectOption[];
  /** Or a provider that lists the projects the user can access. */
  provider?: ProjectProvider;
  /** Currently active project id, if any (shown on the trigger). */
  current?: string | null;
  /** Trigger placeholder when nothing is active. */
  placeholder?: string;
  /** The app's own manifest scope; overrides the page marker when the app knows it. */
  scope?: AppScope;
  /** Navigate on pick, e.g. "?project={id}". Omit to only emit the change event. */
  navigate?: string;
}

/** The host's project list, when the host advertises a provider. */
export { hostProjectProvider };

/**
 * If (and only if) this page's app is project-scoped, mount the shared
 * ProjectSelector into `options.container` and return it; otherwise leave the
 * container empty and return null.
 *
 * Returning the instance (or null) rather than throwing is the point: a
 * user-scoped app is a NORMAL state, not an error, so the caller's
 * `if (sel) sel.container.addEventListener(...)` is the whole adoption.
 */
export function mountProjectSelectorByScope(
  options: AppScopeSelectorOptions,
  doc: Document = document,
): ProjectSelector | null {
  if ((options.scope ?? appScope(doc)) !== SCOPE_PROJECT) {
    // user-scoped / absent: do not render a selector. The container is left
    // exactly as given — nothing appended — which is what "renders with no
    // switcher" means structurally.
    return null;
  }
  const provider =
    options.provider ?? (options.projects ? undefined : hostProjectProvider(doc) ?? undefined);
  const selector = new ProjectSelector({
    container: options.container,
    projects: options.projects,
    provider,
    current: options.current,
    placeholder: options.placeholder,
  });
  const navigate = options.navigate;
  const container =
    typeof options.container === "string"
      ? doc.querySelector<HTMLElement>(options.container)
      : options.container;
  if (navigate && container) {
    container.addEventListener(PROJECT_SELECTOR_CHANGE, (event) => {
      const url = projectNavigationUrl(navigate, (event as CustomEvent<{ id: string }>).detail.id);
      if (url) window.location.assign(url);
    });
  }
  return selector;
}

/** Re-export the change event name so a consumer that only imports from this
 *  module wires its listener without reaching into project-selector directly.
 *  (Single source of truth — this is the same constant ProjectSelector emits.) */
export { PROJECT_SELECTOR_CHANGE };
