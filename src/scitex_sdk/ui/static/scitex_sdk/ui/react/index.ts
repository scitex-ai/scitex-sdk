/**
 * scitex-ui — React component barrel export.
 *
 * Import levels (from most to least specific):
 *   import { FileBrowser } from 'scitex-ui/react/app/file-browser';  // deep
 *   import { FileBrowser } from 'scitex-ui/react/app';               // layer
 *   import { FileBrowser } from 'scitex-ui/react';                   // root
 *
 * CSS: Components reuse the same CSS as the vanilla TS versions.
 *   import 'scitex_sdk/ui/css/app/file-browser.css';
 */

// App components
export * from "./app";

// Shell components — REMOVED: workspace shell is now vanilla TS only
// (see ts/shell/ for the vanilla TS implementation)

// Base types
export type { BaseProps } from "./_base";
