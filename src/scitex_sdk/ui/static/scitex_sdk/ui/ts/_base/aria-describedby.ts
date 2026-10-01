/**
 * Shared `aria-describedby` list management.
 *
 * WHY THIS IS ONE HELPER AND NOT LOGIC IN EACH COMPONENT.
 *
 * `aria-describedby` holds a SPACE-SEPARATED LIST OF IDS, not a single id.
 * Two components can legitimately describe the same element — dim explains why
 * a control is unusable, the tooltip explains what it does — and both are worth
 * hearing.
 *
 * Treating the attribute as a scalar is what creates a collision: each
 * component ASSIGNS, so whichever runs second silently discards the other's
 * description. Nothing throws, nothing renders wrong, and a screen-reader user
 * is simply told one thing instead of two. scitex-app named the fix precisely:
 *
 *     "The ownable unit is not the attribute, it is the ID."
 *
 * So no component ever assigns. Each adds and removes ONLY its own id, and the
 * race stops existing rather than being arbitrated.
 *
 * ORDER MATTERS AND IS NOT COSMETIC. Screen readers announce the list in
 * order, so the ACTIONABLE sentence must arrive before the descriptive one:
 *
 *     "Sign in to use this. Exports the current figure."   <- right
 *     "Exports the current figure. Sign in to use this."   <- the user hears
 *                                                             what it does and
 *                                                             only belatedly
 *                                                             that they cannot
 *
 * Hence the `position` argument rather than a plain append. dim adds "first",
 * the tooltip adds "last", and the resulting order is correct no matter which
 * component happens to run first — which matters because that ordering is not
 * something either component can control.
 *
 * MEASURED (scitex-app, 2026-09-03, Chrome 151 via CDP
 * `Accessibility.getFullAXTree`) — the composition and ordering are FACTS, not
 * hopes:
 *
 *     describedby="dim-reason tip-desc" -> "Sign in to use this. Exports the
 *                                           current figure."
 *     describedby="tip-desc dim-reason" -> the reverse, exactly
 *     describedby="dim-reason missing"  -> "Sign in to use this."
 *
 * Both nodes are included, the order follows the IDREF order precisely, and the
 * parts are joined with a single space. So `position` is a real lever rather
 * than a guess about engine behaviour.
 *
 * THE THIRD ROW IS THE DANGEROUS ONE AND IT SHAPED THE TEARDOWN RULE BELOW. A
 * dangling id does not produce an error, a warning, or a gap — the description
 * computes cleanly to whatever node survives. So a component that fails to
 * remove its id, or that clears the whole attribute, produces an accessibility
 * tree that looks PERFECTLY HEALTHY while silently carrying one description
 * instead of two. That failure is undetectable by inspecting the computed
 * description; it can only be caught by asserting on the attribute's id LIST,
 * which is what this module's tests do.
 *
 * STILL UNVERIFIED, narrowly and deliberately: how the joined string is
 * ANNOUNCED — one utterance or two, where the pause falls, how the full stop is
 * handled. That is reader-specific prosody, no screen reader is available to
 * either package (orca / espeak / spd-say / nvda all absent, measured), and
 * reading the string tells you what it SAYS rather than how it SOUNDS. The
 * ordering argument above stands on the measurement; only the prosody is open,
 * and a real reader beats the reasoning if anyone gets one.
 */

const ATTR = "aria-describedby";

function ids(el: HTMLElement): string[] {
  const raw = el.getAttribute(ATTR);
  return raw ? raw.split(/\s+/).filter(Boolean) : [];
}

function write(el: HTMLElement, list: string[]): void {
  if (list.length === 0) {
    // Remove the attribute rather than leaving it empty: an empty
    // aria-describedby is not the same as an absent one to every reader, and
    // "" is a value some implementations treat as a dangling reference.
    el.removeAttribute(ATTR);
    return;
  }
  el.setAttribute(ATTR, list.join(" "));
}

/**
 * Add `id` to the element's description list, if not already present.
 *
 * `position` decides where it lands relative to descriptions other components
 * have already added — "first" for an actionable reason, "last" for an
 * ordinary description. Idempotent: adding an id already in the list leaves
 * the list, and its order, untouched.
 */
export function addDescribedBy(
  el: HTMLElement,
  id: string,
  position: "first" | "last" = "last",
): void {
  const list = ids(el);
  if (list.includes(id)) return;
  write(el, position === "first" ? [id, ...list] : [...list, id]);
}

/**
 * Remove ONLY `id`, leaving every other component's description in place.
 *
 * This is the half that breaks quietly. A component that clears the attribute
 * on teardown removes descriptions it does not own, and the symptom — one
 * description instead of two — is invisible to anyone not listening for the
 * missing one.
 */
export function removeDescribedBy(el: HTMLElement, id: string): void {
  const list = ids(el);
  if (!list.includes(id)) return;
  write(
    el,
    list.filter((each) => each !== id),
  );
}

/** The current description ids, in announcement order. Exported for tests. */
export function describedByIds(el: HTMLElement): string[] {
  return ids(el);
}
