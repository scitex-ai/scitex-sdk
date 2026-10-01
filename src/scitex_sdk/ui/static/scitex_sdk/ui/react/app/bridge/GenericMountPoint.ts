/**
 * GenericMountPoint — shared React mount + fetch override for app bridges.
 *
 * Apps call these helpers from their own bridge/MountPoint.ts instead of
 * reimplementing fetch interception and React root management.
 */

import React from "react";
import { createRoot, Root } from "react-dom/client";
import type { BridgeConfig } from "./BridgeContract";

let root: Root | null = null;
let rootContainer: HTMLElement | null = null;
const installedOverrides = new Set<string>();

/**
 * Install a fetch override that rewrites matching API paths.
 *
 * Paths matching any prefix in `config.apiPaths` are rewritten from
 * `/{path}` to `/apps/{slug}/{slug}/{path}`.
 *
 * Safe to call multiple times — only installs once per slug.
 */
export function installFetchOverride(config: BridgeConfig): void {
  if (installedOverrides.has(config.slug)) return;

  const originalFetch = window.fetch;
  window.fetch = function (input: RequestInfo | URL, init?: RequestInit) {
    if (typeof input === "string" && input.startsWith("/")) {
      const pathOnly = input.split("?")[0];
      const isAppPath = config.apiPaths.some(
        (prefix) => pathOnly === prefix || pathOnly.startsWith(prefix),
      );
      if (isAppPath) {
        input = `/apps/${config.slug}/${config.slug}${input}`;
      }
    }
    return originalFetch.call(window, input, init);
  };

  installedOverrides.add(config.slug);
}

/**
 * Mount a React element into the given container.
 *
 * Cleans up any previous mount first.
 */
export function mountReactApp(
  container: HTMLElement,
  element: React.ReactElement,
): void {
  if (root) {
    root.unmount();
    root = null;
  }
  root = createRoot(container);
  rootContainer = container;
  root.render(element);
}

/**
 * Unmount the currently mounted React app and clean up. A container lets an
 * outgoing app clean up its own mount without tearing down its successor.
 */
export function unmountReactApp(container?: HTMLElement): void {
  if (container && container !== rootContainer) return;
  if (root) {
    root.unmount();
    root = null;
    rootContainer = null;
  }
}
