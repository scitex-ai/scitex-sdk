/**
 * Chat message persistence — localStorage.
 *
 * Ported from scitex-cloud's storage.ts.
 */

import type { StoredMessage } from "./types";

const STORAGE_KEY = "stx-shell-ai-conversation";
const MAX_STORED = 40;

export function saveMessage(msg: StoredMessage): void {
  const stored = loadMessages();
  stored.push(msg);
  if (stored.length > MAX_STORED) stored.splice(0, stored.length - MAX_STORED);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  } catch {
    /* storage full */
  }
}

export function loadMessages(): StoredMessage[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function clearMessages(): void {
  localStorage.removeItem(STORAGE_KEY);
}
