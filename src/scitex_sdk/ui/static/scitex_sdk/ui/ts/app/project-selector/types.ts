/**
 * Type definitions for the ProjectSelector component: the SDK project picker
 * a project-scope app places inside its own UI (never the global header).
 */

import type { BaseComponentConfig } from "../../_base/types";
import type { ProjectProvider } from "./provider";

export interface ProjectOption {
  /** Stable project identifier (passed back via the change event). */
  id: string;
  /** Display name (what the user sees on the trigger and in the list). */
  name: string;
  /** Optional secondary line under the name (owner, path, host...). */
  detail?: string;
}

export interface ProjectSelectorConfig extends BaseComponentConfig {
  /** A fixed project list. Use `provider` instead when the host serves the list. */
  projects?: ProjectOption[];
  /** Supplies the projects the user can access, and remembers the last visited one. */
  provider?: ProjectProvider;
  /** Currently selected project id. When set it beats the provider's default. */
  current?: string | null;
  /** Trigger text when nothing is selected. Defaults to "Select project". */
  placeholder?: string;
  /** Hide the fuzzy search box (it is shown by default). */
  searchable?: boolean;
}
