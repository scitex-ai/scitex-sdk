/**
 * Fuzzy matching for the project picker: a case-insensitive subsequence match
 * ranked so prefixes, word starts and contiguous runs float to the top.
 */

const WORD_BOUNDARY = /[\s/_\-.]/;

/** Score how well `query` matches `text`; null when it does not match at all. */
export function fuzzyScore(query: string, text: string): number | null {
  const needle = query.trim().toLowerCase();
  if (needle === "") return 0;
  const haystack = text.toLowerCase();

  let score = 0;
  let from = 0;
  let previous = -2;
  for (const char of needle) {
    const index = haystack.indexOf(char, from);
    if (index === -1) return null;
    if (index === previous + 1) score += 5;
    if (index === 0) score += 8;
    else if (WORD_BOUNDARY.test(haystack[index - 1])) score += 4;
    score -= Math.min(index - from, 3);
    previous = index;
    from = index + 1;
  }
  if (haystack.includes(needle)) score += 10;
  // Shorter names win ties so "writer" beats "writer-archive-2019".
  return score - haystack.length * 0.01;
}

/** Items matching `query`, best first; an empty query keeps the original order. */
export function fuzzyFilter<T>(
  items: readonly T[],
  query: string,
  textOf: (item: T) => string,
): T[] {
  if (query.trim() === "") return [...items];
  return items
    .map((item, order) => ({ item, order, score: fuzzyScore(query, textOf(item)) }))
    .filter((entry): entry is { item: T; order: number; score: number } => entry.score !== null)
    .sort((a, b) => b.score - a.score || a.order - b.order)
    .map((entry) => entry.item);
}
