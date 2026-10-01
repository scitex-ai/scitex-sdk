/**
 * scitex-ui — root barrel export.
 *
 * Import levels (from most to least specific):
 *   import { AppShell } from 'scitex-ui/ts/shell/app-shell';  // deep
 *   import { AppShell } from 'scitex-ui/ts/shell';             // layer
 *   import { AppShell } from 'scitex-ui/ts';                   // root
 */

// Shell components
export * from "./shell";

// App components
export * from "./app";

// Base (for custom component authors)
export { BaseComponent } from "./_base";
export type { BaseComponentConfig } from "./_base";
