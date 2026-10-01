/**
 * Command history for AI chat input — bash-style C-p / C-n navigation.
 *
 * Ported from scitex-cloud's history.ts.
 */

const HISTORY_KEY = "stx-shell-ai-history";
const MAX_HISTORY = 50;

export function loadHistory(): string[] {
  try {
    const saved = localStorage.getItem(HISTORY_KEY);
    return saved ? (JSON.parse(saved) as string[]) : [];
  } catch {
    return [];
  }
}

export function pushHistory(history: string[], text: string): string[] {
  if (!text || text === history[0]) return history;
  const next = [text, ...history].slice(0, MAX_HISTORY);
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(next));
  } catch {
    /* storage full */
  }
  return next;
}
