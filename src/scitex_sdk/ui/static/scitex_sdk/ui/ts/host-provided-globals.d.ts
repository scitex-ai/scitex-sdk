/**
 * Globals the HOST APPLICATION provides, which our code consumes but does not
 * define. Declaring them here is what lets us typecheck code that talks to the
 * host without pretending we own the implementation.
 *
 * Ambient by construction: this file has no top-level import/export, so its
 * declarations merge into the global scope. Every entry must name the repo that
 * actually implements it, so a reader can go read the real thing.
 */

/**
 * Navigation state the host's history engine round-trips through
 * `history.pushState`. Mirrors `NavState` in scitex-cloud
 * `static/shared/ts/app-navigation-history.ts`.
 */
interface AppNavigationState {
  _scitex: true;
  module: string;
  file?: string;
  aiMode?: string;
  timestamp: number;
}

/**
 * The host's unified in-app navigation engine, implemented by scitex-cloud
 * `static/shared/ts/app-navigation-history.ts` (which assigns `window._appNav`).
 * Absent when our components run outside that host — hence optional on `Window`,
 * and every call site must guard with `?.`.
 */
interface AppNavigationHistory {
  /** Push a new history entry (module switch, file open). */
  push(state: Partial<Omit<AppNavigationState, "_scitex" | "timestamp">>): void;
  /** Update the current history entry in place. */
  replace(
    state: Partial<Omit<AppNavigationState, "_scitex" | "timestamp">>,
  ): void;
  /** Register a handler run on back/forward. */
  onRestore(handler: (state: AppNavigationState) => void): void;
}

interface Window {
  _appNav?: AppNavigationHistory;
}
