/**
 * Type definitions for the Dim component — the presentation half of an
 * authorization verdict.
 *
 * THE VERDICT IS PRODUCED ELSEWHERE. `scitex_sdk.app.authz` builds it; this package
 * only renders it. The value crosses the package boundary as PLAIN SERIALISABLE
 * DATA (scitex-app's `Verdict.to_dict()`), which is why scitex-ui does not and
 * must not depend on scitex-app: an app depends on both of us, so importing the
 * SDK here would point that arrow backwards and every consumer would inherit it
 * through the presentation layer.
 *
 * THE KIND STRINGS BELOW ARE A SECOND COPY of scitex_sdk.app.authz's, in another
 * repo, and nothing in this file can detect a rename on their side.
 * Deliberately not numbered here: this sentence said "THE FOUR" until
 * `unresolved` was added 2026-09-05, so the count went stale on the very first
 * addition and did so SILENTLY, which is what prose gets wrong that a test gets
 * right. The count is asserted in
 * tests/develop/test_dim_renders_a_verdict.py, where growing the union turns it
 * red instead of leaving a comment quietly lying to the next reader.
 * scitex-app is building the check that can (it reads these constants out of
 * this package's shipped source), and it runs on THEIR side deliberately: the
 * breakage would appear here, but the cause is there, so a check nearest the
 * rename prevents rather than detects. Their caveat, recorded because it is
 * load-bearing: that leg is currently a RECORD, not a required context.
 *
 * EACH KIND RECORDS THE RELEASE IT FIRST SHIPPED IN, and that is not
 * decoration. A consumer comparing its own kind set against this file cannot
 * otherwise tell two different situations apart:
 *
 *     installed scitex-ui predates the kind   the contract cannot be evaluated
 *     installed scitex-ui postdates it        the contract is VIOLATED
 *
 * Without the version those collapse into one red, and the honest answer to the
 * first is "unknown" rather than "no" — the three-valued rule, applied to a
 * cross-package check. scitex-app hit exactly this on 2026-09-05: their CI
 * installs scitex-ui unpinned, so a propagation-window install of an older
 * wheel reported a contract violation that was true of the installation and
 * false of the contract.
 *
 * These are HISTORICAL facts, which is why they are safe to write here when a
 * claim about scitex-app's current implementation would not be. "unresolved
 * ships from 0.20.2" cannot stop being true; "scitex-app parses this union"
 * stops being true the day they change it, silently, with nothing to catch it.
 * Measured from the published wheels rather than recalled — 0.19.1 has no
 * types.ts at all, 0.20.0 and 0.20.1 carry four kinds, 0.20.2 carries five.
 */

/**
 * Permitted. The only kind that is not a denial.
 *
 * Ships from scitex-ui 0.20.0.
 */
export const ALLOWED = "allowed";

/**
 * Refused, with no further recourse to offer.
 *
 * Ships from scitex-ui 0.20.0.
 */
export const DENIED = "denied";

/**
 * Refused because nobody is signed in. Carries a route.
 *
 * Ships from scitex-ui 0.20.0.
 */
export const DENIED_NOT_SIGNED_IN = "denied-because-not-signed-in";

/**
 * Refused because the signed-in account lacks the entitlement.
 *
 * Ships from scitex-ui 0.20.0.
 */
export const DENIED_NOT_ENTITLED = "denied-because-not-entitled";

/**
 * Authorization could not be DETERMINED — resolution was attempted and failed.
 *
 * Distinct from `denied` in the way that matters to a person: `denied` is an
 * answer, this is the absence of one. Collapsing it into `denied` would tell a
 * user "no" when the truth is "we could not ask", and collapsing it into
 * `allowed` would open a control on a permission nobody verified.
 *
 * ADDED 2026-09-05, and only because the implementation demanded it. The
 * standing agreement with scitex-app was that a fifth kind arrives when a
 * concrete case has no verdict to return, decided jointly — not whenever one
 * seems tidy. That case is the A/B decomposition's tri-state resolve: when
 * resolution is ATTEMPTED AND FAILS there is no member of the previous four
 * that is true.
 *
 * ONE kind, not one per axis. Per-axis variants would multiply with every new
 * axis and leak which axis failed, which is system-internal structure.
 *
 * Ships from scitex-ui 0.20.2.
 */
export const UNRESOLVED = "unresolved";

export type VerdictKind =
  | typeof ALLOWED
  | typeof DENIED
  | typeof DENIED_NOT_SIGNED_IN
  | typeof DENIED_NOT_ENTITLED
  | typeof UNRESOLVED;

export interface AllowedVerdict {
  kind: typeof ALLOWED;
}

export interface DeniedVerdict {
  kind: typeof DENIED;
}

export interface DeniedNotSignedInVerdict {
  kind: typeof DENIED_NOT_SIGNED_IN;
  /**
   * Where the user can go to sign in.
   *
   * REQUIRED, not optional, and that is enforced upstream rather than here:
   * scitex-app's validator REFUSES to build this kind without it, and refuses
   * to attach it to any other kind. So a verdict that reaches this component
   * cannot carry a sign-in route it has no business carrying, and cannot omit
   * one it promised. No defensive branch is written for either case on purpose
   * — an unnecessary guard is where a future bug hides, and it makes the
   * upstream guarantee look untrusted so the next reader adds another.
   */
  sign_in_url: string;
}

export interface DeniedNotEntitledVerdict {
  kind: typeof DENIED_NOT_ENTITLED;
  /** The entitlement the account is missing, e.g. a plan name. */
  entitlement: string;
  /**
   * NO ROUTE TODAY, and its absence is a decision rather than an oversight.
   *
   * "Sign in" is an action a user can take right now; "you are not on the paid
   * plan" may not be. Whether hub has an upgrade surface to send them to is
   * hub's fact, and scitex-app is asking rather than inventing it. Until there
   * is an answer, this kind renders inert — because a control that promises a
   * destination which does not exist is exactly the defect scitex-app's
   * validator refuses at the type level, relocated into CSS.
   *
   * WHEN IT ARRIVES it is an `upgrade_url` PAYLOAD on this interface, NOT a
   * fifth kind (scitex-app confirmed the shape 2026-09-03). That distinction is
   * why this switch is safe: adding a payload field is backward compatible and
   * leaves exhaustiveness intact, whereas a fifth kind would break it and needs
   * coordination on both sides.
   */
}

export interface UnresolvedVerdict {
  kind: typeof UNRESOLVED;
  /**
   * NO PAYLOAD, and the omission is the decision.
   *
   * The obvious field is a reason — network, misconfiguration, timeout. I asked
   * scitex-app for it; they refused, using the argument I had used on them a day
   * earlier about axis names: a failure reason is system-internal state, and
   * "timeout" told to an unauthenticated visitor discloses availability of the
   * service behind the gate. It is strictly worse than the axis name we already
   * decided to keep out of the DOM.
   *
   * The second reason is Decision 1's: a value that does not change what the UI
   * does has no business in the page source. The only motive left is debugging
   * convenience, and that is a server-side log's job.
   *
   * Their validator REFUSES a payload on this kind at construction, the same
   * one-directional way it refuses `sign_in_url` where it does not belong.
   */
}

/**
 * A discriminated union, so a `switch` over `kind` is checked for
 * exhaustiveness by the compiler rather than by a reviewer.
 *
 * DELIBERATELY NO `allowed` BOOLEAN, here or anywhere in this component. A
 * helper like `isAllowed(v)` would be shorter than `v.kind === ALLOWED`, read
 * naturally, pass review, and silently collapse "sign in and this works" into
 * "this will never work" — the two-valued collapse of a genuinely multi-valued
 * answer. scitex-app asserts its absence on their side; a test in this repo
 * asserts it on ours, so the convenience cannot reappear without someone
 * deciding to add it.
 */
export type Verdict =
  | AllowedVerdict
  | DeniedVerdict
  | DeniedNotSignedInVerdict
  | DeniedNotEntitledVerdict
  | UnresolvedVerdict;

/**
 * Human-readable reason text, one per denial.
 *
 * Configurable rather than hardcoded because this package already treats the
 * document language as dynamic (`shell_lang`), and a component that bakes
 * English strings into the accessible description would quietly undo that for
 * the one piece of text a screen-reader user most needs.
 */
export interface DimLabels {
  denied: string;
  deniedNotSignedIn: string;
  /** Receives the entitlement name via `{entitlement}`. */
  deniedNotEntitled: string;
  /**
   * Shown when authorization could not be determined.
   *
   * Must say that the ANSWER is missing, not that the answer is no. "Could not
   * check" and "not allowed" send a user to different places — the first
   * invites a retry, the second ends the interaction — and this component's
   * whole reason for existing is that a person can act on the difference.
   */
  unresolved: string;
}

export interface DimConfig {
  /** Override any subset of the reason strings. */
  labels?: Partial<DimLabels>;
}
