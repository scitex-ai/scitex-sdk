/**
 * Where the project picker gets its projects from.
 *
 * The host decides what "projects this user can access" means (the hub: owned
 * plus shared; a standalone app: local project folders). The picker only
 * talks to this interface, so it never imports an access-control library.
 */

import type { ProjectOption, ProjectSelection } from "./types";

export interface ProjectListing {
  projects: ProjectOption[];
  /** The host's default: the explicit project of this page, else the last visited one. */
  current?: string | null;
  /** Optional explicit capability/current scope supplied by a supporting host. */
  allow_user_scope?: boolean;
  current_scope?: "user" | "project";
}

export interface ProjectProvider {
  listProjects(): Promise<ProjectListing>;
  /** Persist the choice as the user's last visited project. Optional. */
  rememberProject?(id: string): Promise<void>;
  /** Opt-in host port. Resolve only after the explicit scope choice is accepted.
   * Legacy POST {id} is not this contract; user scope must never go through it. */
  rememberScope?(selection: ProjectSelection): Promise<void>;
}

/** A provider over a fixed list (tests, demos, apps that already hold the data). */
export function staticProjectProvider(
  projects: ProjectOption[],
  current: string | null = null,
): ProjectProvider {
  return {
    listProjects: async () => ({ projects, current }),
  };
}

function csrfToken(): string {
  if (typeof document === "undefined" || typeof document.cookie !== "string") return "";
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

/** Meta the host stamps to advertise its project provider endpoint.
 *  Mirrors scitex_sdk.ui.project_scope.PROJECT_PROVIDER_META_NAME. */
export const PROJECT_PROVIDER_META_NAME = "stx-project-provider";

export interface HttpProjectProviderOptions {
  /** Request the supporting host's scoped protocol. Off for legacy callers. */
  allowUserScope?: boolean;
}

// Both shipped picker entrypoints bundle this module independently. A shared
// symbol keeps an injected transport recognizable across those entrypoints.
const SCOPED_HTTP_TRANSPORT = Symbol.for("scitex-sdk.ui.scoped-http-project-provider");

/** A pending scoped HTTP transport, not evidence of server capability or permission. */
export function usesScopedHttpTransport(provider: ProjectProvider | undefined): boolean {
  return provider !== undefined && Reflect.get(provider, SCOPED_HTTP_TRANSPORT) === true;
}

/** The host's project provider (the hub's project list), or null when the page has none. */
export function hostProjectProvider(
  doc: Document = document,
  options: HttpProjectProviderOptions = {},
): ProjectProvider | null {
  const url = doc.querySelector(`meta[name="${PROJECT_PROVIDER_META_NAME}"]`)?.getAttribute("content");
  return url ? httpProjectProvider(url, options) : null;
}

/**
 * The HTTP provider contract, served by the SDK's Django view and by the hub:
 *   GET  <url>            -> {"projects": [{id, name, detail?}], "current": id|null}
 *   POST <url> {"id": id} -> remembers the last visited project
 */
export function httpProjectProvider(
  url: string,
  options: HttpProjectProviderOptions = {},
): ProjectProvider {
  const scoped = options.allowUserScope === true;
  let authority = 0;
  let enabled = false;
  const provider: ProjectProvider = {
    async listProjects(): Promise<ProjectListing> {
      const listingAuthority = scoped ? ++authority : authority;
      if (scoped) {
        enabled = false;
        delete provider.rememberScope;
      }
      const response = await fetch(url, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`project listing failed: HTTP ${response.status}`);
      const body = (await response.json()) as ProjectListing;
      if (!scoped) return { projects: body.projects ?? [], current: body.current ?? null };
      if (body.allow_user_scope !== true || !Array.isArray(body.projects)) {
        throw new Error("scoped project provider is not enabled");
      }
      const scope = body.current_scope;
      const current = body.current ?? null;
      if ((scope !== undefined && scope !== "user" && scope !== "project") ||
          (scope === "user" && body.current !== null) ||
          (scope === "project" && (typeof current !== "string" || !current.trim())) ||
          (scope === undefined && current !== null)) {
        throw new Error("invalid current scope selection");
      }
      if (authority !== listingAuthority) throw new Error("scope listing superseded");
      enabled = true;
      provider.rememberScope = rememberScope;
      return {
        projects: body.projects, current, allow_user_scope: true,
        ...(scope === undefined ? {} : { current_scope: scope }),
      };
    },
    async rememberProject(id: string): Promise<void> {
      if (typeof id !== "string" || !id.trim()) throw new Error("project id required");
      const response = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
        body: JSON.stringify({ id }),
      });
      if (!response.ok) throw new Error(`project selection failed: HTTP ${response.status}`);
    },
  };

  async function rememberScope(selection: ProjectSelection): Promise<void> {
    if (!enabled || provider.rememberScope !== rememberScope) {
      throw new Error("scoped project provider is not enabled");
    }
    const { scope, id } = selection;
    if (scope === "user" ? id !== null :
        scope !== "project" || typeof id !== "string" || !id.trim()) {
      throw new Error("explicit scope selection required");
    }
    const requested = { scope, id };
    const acceptedAuthority = authority;
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      body: JSON.stringify(requested),
    });
    if (!response.ok) throw new Error(`scope selection failed: HTTP ${response.status}`);
    const body = (await response.json()) as ProjectListing;
    if (body.current_scope !== requested.scope || body.current !== requested.id) {
      throw new Error("scope selection acknowledgement does not match");
    }
    if (!enabled || authority !== acceptedAuthority || provider.rememberScope !== rememberScope) {
      throw new Error("scope provider authority changed");
    }
  }

  if (scoped) Object.defineProperty(provider, SCOPED_HTTP_TRANSPORT, { value: true });
  return provider;
}
