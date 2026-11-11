/**
 * SciTeX SDK frontend barrel exports.
 *
 * Import common primitives from the public package:
 *   import { csrfToken } from "@scitex/sdk/ui/ts";
 * Component-specific exports are available under "@scitex/sdk/ui/ts/...".
 */

// Shell components
export * from "./shell";

// App components
export * from "./app";

// Base (for custom component authors)
export { BaseComponent, csrfToken } from "./_base";
export type { BaseComponentConfig } from "./_base";
