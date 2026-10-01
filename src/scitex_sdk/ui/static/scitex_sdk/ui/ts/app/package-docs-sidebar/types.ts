/**
 * Type definitions for the PackageDocsSidebar component.
 */

import type { BaseComponentConfig } from "../../_base/types";

export interface PackageInfo {
  name: string;
  version: string;
  description?: string;
  group?: string;
  icon?: string;
  url?: string;
}

export interface PackageDocsSidebarConfig extends BaseComponentConfig {
  /** API endpoint to fetch package list */
  apiUrl?: string;
  /** Called when user clicks a package */
  onPackageSelect?: (pkg: PackageInfo) => void;
}
