/**
 * stx-app-scope — who am I scoped to? (consumer half of the scitex-app SDK
 * contract, operator ledger #48 / #144-149, PR scitex-app #185 @ d8528de4).
 *
 * The SERVER (scitex_app's `_app_scope.py`) declares each leaf app's scope in
 * its manifest and, for PROJECT-scoped apps ONLY, injects a marker into the
 * document head:
 *
 *     <meta name="stx-app-scope" content="project">
 *
 * A user-scoped app (or one that omits `scope` — the SDK's safe default)
 * emits NOTHING. That asymmetry is the whole contract, and it inverts the
 * reader's semantics relative to the sibling stx-mount marker in
 * ./mount.ts:
 *
 *   stx-mount    missing  -> ERROR (an app can't guess where it is mounted)
 *   stx-app-scope missing  -> "user" (the safe direction: NO selector)
 *
 * So `appScope()` NEVER throws on absence. The one thing it refuses is a
 * GUESS: an unrecognised value (a typo'd scope, a third value the contract
 * later added) must not silently read as "user" and suppress a project
 * selector the app needs. It raises on unknown content, exactly the way
 * scitex-app's `normalize_scope` raises on a typo'd manifest scope — the
 * two ends of the same closed enum failing loud rather than degrading.
 *
 * This module is dependency-free (reads a meta tag, returns a string) so it
 * can be used by both the app-local selector host (./shell/app-scope-
 * selector.ts) and plain consumer scripts. It is the consumer-side twin of
 * scitex_app's producer-side _app_scope.py: same meta name, same value set,
 * mirrored precedence.
 */

/** Meta name the scitex-app SDK injects for project-scoped apps.
 *  MUST stay byte-identical to scitex_sdk.app._app_scope.SCOPE_META_NAME —
 *  pinned by tests/develop/test_app_scope_marker_contract.py against the
 *  SDK's own test, so a rename on either side fails here, not at a leaf. */
export const APP_SCOPE_META_NAME = "stx-app-scope";

/** The scope the marker names. Absence of the marker means SCOPE_USER. */
export const SCOPE_USER = "user";
export const SCOPE_PROJECT = "project";

export type AppScope = typeof SCOPE_USER | typeof SCOPE_PROJECT;

/** Raised when the marker is present but carries a value the contract does
 *  not define. A silent default here would either force a selector onto a
 *  user-scoped app (wrong: the ruling forbids it) or suppress one a
 *  project-scoped app needs (wrong: the app is half-dead). Fail loud. */
export class AppScopeMarkerInvalidError extends Error {
  constructor(content: string | null) {
    super(
      `scitex-ui: <meta name="${APP_SCOPE_META_NAME}"> is present with ` +
        `content=${JSON.stringify(content)}, which is not one of ` +
        `"${SCOPE_USER}" | "${SCOPE_PROJECT}". The scitex-app SDK emits ` +
        `only "project" (user-scoped apps emit NO marker at all), so a ` +
        `present-but-unrecognised marker means the two sides disagree — ` +
        `a renamed value or a stale build. This is an integration bug; ` +
        `scitex-ui will not guess a scope.`,
    );
    this.name = "AppScopeMarkerInvalidError";
  }
}

/**
 * This app's declared scope, read from the stx-app-scope marker.
 *
 *   - marker absent                -> SCOPE_USER   (the safe default: no selector)
 *   - marker content="project"     -> SCOPE_PROJECT
 *   - marker content="user"        -> SCOPE_USER   (accepted for symmetry;
 *                                                  the SDK emits none, but a
 *                                                  template that writes it is
 *                                                  not wrong)
 *   - marker any other value       -> throws AppScopeMarkerInvalidError
 */
export function appScope(doc: Document = document): AppScope {
  const meta = doc.querySelector(`meta[name="${APP_SCOPE_META_NAME}"]`);
  if (!meta) return SCOPE_USER;
  const raw = meta.getAttribute("content");
  const content = raw === null ? null : raw.trim().toLowerCase();
  if (content === SCOPE_PROJECT) return SCOPE_PROJECT;
  if (content === SCOPE_USER || content === null || content === "") {
    // A present-but-empty marker is the SDK's user-scoped spelling
    // (scope_meta_tag returns "" and _inject_scope_meta skips the insert);
    // tolerate it as user rather than calling it invalid.
    return SCOPE_USER;
  }
  throw new AppScopeMarkerInvalidError(raw);
}

/** True only for the one scope that may offer an app-local project selector.
 *  This is the predicate a consuming surface tests — deliberately named for
 *  the capability, not the scope word, so the call site reads as intent:
 *  `if (mayOfferProjectSelector()) { … }` — and so that "user" / "absent" /
 *  anything-unknown-but-valid all flow through the ONE place that decides
 *  selector-eligibility. */
export function mayOfferProjectSelector(doc: Document = document): boolean {
  return appScope(doc) === SCOPE_PROJECT;
}
