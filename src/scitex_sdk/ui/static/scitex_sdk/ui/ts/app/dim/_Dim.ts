/**
 * Dim — render an authorization verdict onto a control that stays visible.
 *
 * Usage:
 *   import { applyVerdict } from 'scitex_sdk/ui/ts/app/dim';
 *   applyVerdict(button, { kind: "denied-because-not-signed-in",
 *                          sign_in_url: "/accounts/signin" });
 *
 * WHY `aria-disabled` AND NEVER THE `disabled` ATTRIBUTE. The operator's ruling
 * is that a feature you cannot use yet stays VISIBLE and INACTIVE — not hidden,
 * and not behind a login wall. `disabled` removes the control from tab order,
 * which takes the explanation with it: a keyboard user would never reach the
 * one piece of text telling them that signing in would fix this. `aria-disabled`
 * keeps the control focusable and describable while still announcing that it
 * cannot be operated. That single choice is most of the accessibility argument
 * for dim existing as its own state.
 *
 * WHY THIS DOES NOT USE THE TOOLTIP COMPONENT. `app/tooltip` binds `mouseenter`
 * and `mouseleave` only — no focus, no `aria-describedby` (measured 2026-09-03).
 * It is mouse-only, so delegating the reason to it would put the explanation
 * exactly where a keyboard user cannot get it, undoing the reason we chose
 * `aria-disabled` in the first place. Dim therefore owns its accessible
 * description. The tooltip's missing focus support is a real defect in its own
 * right and is carded separately rather than fixed here, so that a change to
 * tooltips and a change to dim never land together with one observable
 * difference between them.
 */

import {
  addDescribedBy,
  removeDescribedBy,
} from "../../_base/aria-describedby";
import {
  ALLOWED,
  DENIED,
  DENIED_NOT_ENTITLED,
  DENIED_NOT_SIGNED_IN,
  UNRESOLVED,
} from "./types";
import type { DimConfig, DimLabels, Verdict } from "./types";

const CLS = "stx-app-dim";
const CLS_ACTIONABLE = `${CLS}--actionable`;
const CLS_REASON = `${CLS}__reason`;

/** Carries the sign-in route for the (separate) sign-in control to consume. */
const ATTR_SIGN_IN_URL = "data-stx-dim-sign-in-url";

const DEFAULT_LABELS: DimLabels = {
  denied: "Not available.",
  deniedNotSignedIn: "Sign in to use this.",
  deniedNotEntitled: "Requires {entitlement}.",
  // Says the ANSWER is missing, not that the answer is no, and names no cause.
  // "Could not check" invites a retry; "Not available" ends the interaction.
  unresolved: "Could not check availability right now.",
};

let seq = 0;

/**
 * Reason nodes, keyed by the control they describe, so re-applying a verdict
 * reuses one node instead of accumulating them. Weak so that a control dropped
 * from the DOM does not keep its entry alive.
 */
const reasonNodes = new WeakMap<HTMLElement, HTMLElement>();

function reasonTextFor(verdict: Verdict, labels: DimLabels): string | null {
  switch (verdict.kind) {
    case ALLOWED:
      return null;
    case DENIED:
      return labels.denied;
    case DENIED_NOT_SIGNED_IN:
      return labels.deniedNotSignedIn;
    case DENIED_NOT_ENTITLED:
      return labels.deniedNotEntitled.replace(
        "{entitlement}",
        verdict.entitlement,
      );
    case UNRESOLVED:
      // The answer is MISSING, not negative. Falling through to `denied` here
      // would be the two-valued collapse this component exists to refuse: it
      // would tell a user "no" when the truth is "we could not ask".
      return labels.unresolved;
    default:
      // Unreachable while the union is exhaustive. It is written as an
      // assignment to `never` rather than a thrown error so that a SIXTH KIND
      // added upstream fails at COMPILE time here, not at runtime on a page.
      //
      // It did its job on 2026-09-05: adding `unresolved` to the union broke
      // this compile until the case above existed, which is the entire reason
      // the default is written this way rather than as a thrown Error.
      return assertNever(verdict);
  }
}

function assertNever(value: never): never {
  throw new Error(`Dim: unhandled verdict kind: ${JSON.stringify(value)}`);
}

/**
 * The route this verdict offers, or null when it offers none.
 *
 * Only `denied-because-not-signed-in` carries one today. An entitlement denial
 * deliberately does not: "sign in" is something a user can act on immediately,
 * whereas "you are not on the paid plan" may have nowhere to send them, and a
 * control promising a destination that does not exist is the defect
 * scitex-app's validator refuses at the type level. If hub turns out to have an
 * upgrade surface it arrives as an `upgrade_url` PAYLOAD on the not-entitled
 * kind rather than as a fifth kind, so this function grows a case and the
 * switch above is untouched.
 *
 * `unresolved` returns null for a DIFFERENT reason, worth separating because the
 * two look identical here. Not-entitled has no route because we do not yet know
 * whether a destination exists. Unresolved has no route because there is nothing
 * to route TO: the failure is that authorization could not be determined, and no
 * URL fixes that from the user's side. It renders inert and offers nothing,
 * which is the honest shape of "we could not ask".
 */
function routeFor(verdict: Verdict): string | null {
  return verdict.kind === DENIED_NOT_SIGNED_IN ? verdict.sign_in_url : null;
}

function clear(el: HTMLElement): void {
  el.classList.remove(CLS, CLS_ACTIONABLE);
  el.removeAttribute("aria-disabled");
  el.removeAttribute(ATTR_SIGN_IN_URL);
  el.removeAttribute("data-tooltip");

  const node = reasonNodes.get(el);
  if (node) {
    // Remove ONLY this component's id. The previous version compared the whole
    // attribute to our id and cleared it on a match — correct while dim was the
    // only writer, and wrong the moment app/tooltip began adding its own, since
    // a control described by both would fail that equality check and keep a
    // reference to a node about to be removed.
    //
    // A dangling reference is the silent case: Chrome computes the description
    // cleanly from whatever survives, with no marker that an id went missing
    // (measured by scitex-app, 2026-09-03). So this cannot be caught by
    // inspecting the computed description — only by asserting on the id list.
    removeDescribedBy(el, node.id);
    node.remove();
    reasonNodes.delete(el);
  }
}

function reasonNodeFor(el: HTMLElement): HTMLElement {
  const existing = reasonNodes.get(el);
  if (existing) return existing;

  const node = document.createElement("span");
  node.className = CLS_REASON;
  node.id = `${CLS}-reason-${++seq}`;
  // Placed beside the control rather than inside it: a descendant would be
  // folded into the control's accessible NAME for any element named from its
  // own content (a <button>, most obviously), so "Sync" would announce as
  // "Sync Sign in to use this". As a sibling it is a description only, and it
  // is removed along with the control's container in the ordinary case.
  (el.parentElement ?? document.body).appendChild(node);
  reasonNodes.set(el, node);
  return node;
}

/**
 * Render `verdict` onto `el`.
 *
 * Idempotent, and reversible by design: applying an `allowed` verdict removes
 * every mark a denial left behind. There is no separate `clearVerdict` export,
 * because two ways to express one intent is a menu — the verdict is the input,
 * always, and "allowed" is a verdict rather than the absence of one.
 */
export function applyVerdict(
  el: HTMLElement,
  verdict: Verdict,
  config: DimConfig = {},
): void {
  const labels: DimLabels = { ...DEFAULT_LABELS, ...config.labels };
  const reason = reasonTextFor(verdict, labels);

  if (reason === null) {
    clear(el);
    return;
  }

  el.classList.add(CLS);
  el.setAttribute("aria-disabled", "true");

  // TWO PATHS TO ONE REASON, which is what hub specified ("tooltip /
  // aria-describedby") and not redundancy:
  //   data-tooltip      the VISIBLE path — rendered by app/tooltip
  //   aria-describedby  the ACCESSIBLE path — owned here, added below
  //
  // These stay separate now that app/tooltip HAS focus support, because they
  // answer different questions. The tooltip renders a visible panel; this
  // component's reason node is what assistive technology reads, and it is
  // present whether or not `Tooltip.init()` ever ran. Setting data-tooltip
  // costs nothing when it did not, and the accessible description never
  // depends on it.
  el.setAttribute("data-tooltip", reason);

  const node = reasonNodeFor(el);
  node.textContent = reason;

  // "first" because a denial reason is ACTIONABLE and a tooltip merely
  // DESCRIBES. Screen readers announce the list in IDREF order (measured in
  // Chrome 151), so this puts "Sign in to use this." ahead of "Exports the
  // current figure." — the user learns what they can DO before what the control
  // WOULD do. Position rather than plain append, because neither component can
  // control which of them runs first.
  addDescribedBy(el, node.id, "first");

  const route = routeFor(verdict);
  if (route === null) {
    el.classList.remove(CLS_ACTIONABLE);
    el.removeAttribute(ATTR_SIGN_IN_URL);
  } else {
    el.classList.add(CLS_ACTIONABLE);
    el.setAttribute(ATTR_SIGN_IN_URL, route);
  }
}
