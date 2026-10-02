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

/** The host's project provider (the hub's project list), or null when the page has none. */
export function hostProjectProvider(doc: Document = document): ProjectProvider | null {
  const url = doc.querySelector(`meta[name="${PROJECT_PROVIDER_META_NAME}"]`)?.getAttribute("content");
  return url ? httpProjectProvider(url) : null;
}

/**
 * The HTTP provider contract, served by the SDK's Django view and by the hub:
 *   GET  <url>            -> {"projects": [{id, name, detail?}], "current": id|null}
 *   POST <url> {"id": id} -> remembers the last visited project
 */
export function httpProjectProvider(url: string): ProjectProvider {
  return {
    async listProjects(): Promise<ProjectListing> {
      const response = await fetch(url, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`project listing failed: HTTP ${response.status}`);
      const body = (await response.json()) as ProjectListing;
      return { projects: body.projects ?? [], current: body.current ?? null };
    },
    async rememberProject(id: string): Promise<void> {
      if (typeof id !== "string" || !id.trim()) throw new Error("project id required");
      await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
        body: JSON.stringify({ id }),
      });
    },
  };
}
