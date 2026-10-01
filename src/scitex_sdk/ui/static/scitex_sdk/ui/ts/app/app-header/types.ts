/**
 * AppHeader — mount metadata contract + config types.
 *
 * WHERE THE VALUES COME FROM (the scitex-app contract, not a leaf convention)
 *
 * `data-app-version` is the stable mount metadata attribute the host stamps
 * with the MOUNTED LEAF's own package version (scitex-app
 * `ScitexAppConfig.app_version` / `context_processors.app_version` -> the
 * rendered `{{ app_version }}`). FigRecipe measured the alternative — reading a
 * leaf-local build constant — and it produced a header with the leaf title and
 * ZERO version badge once the app was mounted by the hub, because the hub
 * compiles the leaf's bridge rather than the leaf's dev bundle. So the header
 * reads the ATTRIBUTE, in a fixed precedence, and never guesses.
 *
 * `data-stx-app-header` marks a mount root the pre-built module auto-mounts
 * (same shape as `data-stx-help`).
 */

import type { BaseComponentConfig } from "../../_base/types";

/** Stable mount metadata attribute carrying the leaf's own package version. */
export const APP_VERSION_ATTRIBUTE = "data-app-version";

/** Mount root the pre-built module auto-mounts: `<div data-stx-app-header>`. */
export const HEADER_ATTRIBUTE = "data-stx-app-header";

/** Leaf title, read only when no explicit `title` is passed. */
export const APP_TITLE_ATTRIBUTE = "data-app-title";

export interface AppHeaderConfig extends BaseComponentConfig {
  /** Leaf title. The LEAF owns its translation (pass an already-translated string). */
  title?: string;
  /** Leaf package version. Omitted => the contract payload, then the attributes. */
  version?: string | null;
  /** Badge prefix; the default matches the ecosystem convention (`v0.22.0`). */
  versionPrefix?: string;
  /** App-specific actions, appended in order into the actions slot. */
  actions?: HTMLElement[];
  /**
   * Render the canonical project-selector slot. Omitted => decided by the
   * contract payload: present only for a project-scoped app that declares a
   * provider. A user-scoped app never gets one.
   */
  projectSlot?: boolean;
  /** Inject the payload instead of reading the page's meta tag (tests, SPA boot). */
  shellProps?: ShellProps | null;
}

/**
 * The version to render, by precedence:
 *
 *   1. an explicit value (config.version)
 *   2. `data-app-version` on the mount root the header renders into
 *   3. `data-app-version` on the nearest ANCESTOR carrying it (hub mounts a
 *      leaf inside a container that can carry the stamp)
 *   4. `data-app-version` on `<html>` (host-wide stamp)
 *   5. none -> the badge stays hidden; the header is still valid
 *
 * Returns `null` rather than a placeholder: an unknown version must render as
 * ABSENT, not as a plausible-looking wrong one.
 */
export function resolveAppVersion(
  root: HTMLElement,
  explicit?: string | null,
): string | null {
  if (explicit != null && explicit.trim() !== "") return explicit.trim();

  const own = root.getAttribute(APP_VERSION_ATTRIBUTE);
  if (own && own.trim() !== "") return own.trim();

  const ancestor = root.closest(`[${APP_VERSION_ATTRIBUTE}]`);
  if (ancestor instanceof HTMLElement) {
    const value = ancestor.getAttribute(APP_VERSION_ATTRIBUTE);
    if (value && value.trim() !== "") return value.trim();
  }

  const documentRoot = root.ownerDocument?.documentElement;
  const host = documentRoot?.getAttribute(APP_VERSION_ATTRIBUTE);
  if (host && host.trim() !== "") return host.trim();

  return null;
}

/** Resolve the title: explicit, else `data-app-title`, else empty. */
export function resolveAppTitle(
  root: HTMLElement,
  explicit?: string | null,
): string {
  if (explicit != null && explicit.trim() !== "") return explicit.trim();
  const own = root.getAttribute(APP_TITLE_ATTRIBUTE);
  if (own && own.trim() !== "") return own.trim();
  const ancestor = root.closest(`[${APP_TITLE_ATTRIBUTE}]`);
  if (ancestor instanceof HTMLElement) {
    const value = ancestor.getAttribute(APP_TITLE_ATTRIBUTE);
    if (value && value.trim() !== "") return value.trim();
  }
  return "";
}

/* ── The scitex-app shell contract (the host's props payload) ──────────────
 * scitex-app owns the WRITER: `scitex_sdk.app.shell_contract.inject_shell_props()`
 * emits `<meta name="stx-app-shell" content="{...}">` with the leaf's title,
 * its INSTALLED version, the scope, an optional project provider, the actions
 * and the command registry. This module is the READER half, and the meta name
 * below MUST stay byte-identical to theirs (`SHELL_PROPS_META_NAME`) — a reader
 * looking for a name nobody writes reaches nobody, which is the stx-mount
 * history. scitex-app PR #199 (2026-09-17) is the writer.
 */

/** Mirrors `scitex_sdk.app.shell_contract.SHELL_PROPS_META_NAME`. */
export const SHELL_PROPS_META_NAME = "stx-app-shell";

/** One header action: a control that MUST name a command or an href. */
export interface ShellAction {
  id: string;
  label: string;
  command?: string;
  href?: string;
  order?: number;
}

/** The project provider. Absent on a user-scoped app, where a selector is refused. */
export interface ShellProjectProvider {
  url?: string;
  current?: string | null;
  navigate?: boolean;
  placeholder?: string;
}

export interface ShellCommand {
  label: string;
  group?: string;
  sequence?: string;
}

/** The parsed payload. Keys are the ones scitex-app emits, key-sorted. */
export interface ShellProps {
  app: string;
  title: string;
  version: string;
  scope: string;
  project?: ShellProjectProvider;
  actions?: ShellAction[];
  commands?: Record<string, ShellCommand>;
}

/**
 * Read the shell-props payload, or `null` when the page carries no meta tag.
 *
 * A payload that is PRESENT but unreadable THROWS: a header that renders
 * without its declared actions looks exactly like an app that declares none,
 * and that is the trade the writer already refused to make on its side.
 */
export function readShellProps(doc: Document = document): ShellProps | null {
  const meta = doc.querySelector(
    `meta[name="${SHELL_PROPS_META_NAME}"]`,
  ) as HTMLMetaElement | null;
  if (!meta) return null;
  const raw = meta.getAttribute("content") ?? "";
  try {
    const parsed = JSON.parse(raw) as ShellProps;
    if (!parsed || typeof parsed !== "object") {
      throw new TypeError("payload is not an object");
    }
    return parsed;
  } catch (error) {
    throw new Error(
      `AppHeader: <meta name="${SHELL_PROPS_META_NAME}"> carries an unreadable ` +
        `payload (${(error as Error).message}). Refusing to render a header ` +
        `that would silently drop the app's declared actions.`,
    );
  }
}

/** Actions in render order: `order` first (ascending), then declaration order. */
export function orderedActions(actions: ShellAction[] = []): ShellAction[] {
  return actions
    .map((action, index) => ({ action, index }))
    .sort((a, b) => {
      const byOrder = (a.action.order ?? 0) - (b.action.order ?? 0);
      return byOrder !== 0 ? byOrder : a.index - b.index;
    })
    .map((entry) => entry.action);
}
