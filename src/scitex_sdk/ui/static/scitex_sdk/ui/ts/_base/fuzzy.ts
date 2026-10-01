/**
 * Fuzzy subsequence matching — the one implementation.
 *
 * Every list in the fleet that lets a user narrow it should narrow it the SAME
 * WAY, or the muscle memory does not transfer: typing `sui` finding
 * `scitex-ui` in one picker and nothing in the next is worse than having no
 * filter in the second, because the user learns to distrust the first.
 *
 * Extracted from Combobox when Dropdown needed the same behaviour. Writing a
 * second copy would have been the exact duplication this package exists to
 * remove, and the two copies would have drifted the first time either was
 * "improved".
 */

/**
 * fzf-style subsequence match: every character of `query` must appear in
 * `hay` IN ORDER, though not necessarily consecutively.
 *
 * Both arguments are expected to be already case-normalised by the caller —
 * normalising here would hide the cost from callers filtering on every
 * keystroke, and callers that lowercase their haystack once are strictly
 * better off.
 */
export function fuzzyMatch(query: string, hay: string): boolean {
  if (!query) return true;
  let i = 0;
  for (const c of query) {
    const found = hay.indexOf(c, i);
    if (found < 0) return false;
    i = found + 1;
  }
  return true;
}
