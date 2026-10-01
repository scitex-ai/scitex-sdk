/**
 * OSC Escape Sequence Handler — extracts custom escape sequences from terminal data.
 *
 * Ported from scitex-cloud's console-terminal-factory.ts.
 *
 * Supported sequences:
 *  - \x1b]9999;speak:<base64>\x07 — Text-to-speech
 *  - \x1b]9998;media:<base64>\x07 — Media overlay (image, file download)
 */

import type { TerminalInstance } from "./types";

/** Callback for handling extracted OSC data. */
export type OscCallback = (payload: string) => void;

/** Registry of OSC handlers. */
export interface OscHandlerEntry {
  prefix: string;
  handler: OscCallback;
}

/**
 * Process terminal data, extracting and handling OSC escape sequences.
 * Returns the remaining data after OSC sequences are removed, or null if nothing remains.
 */
export function processOscEscapes(
  data: string,
  handlers: OscHandlerEntry[],
): string | null {
  let remaining = data;
  for (const { prefix, handler } of handlers) {
    remaining = extractOsc(remaining, prefix, handler);
  }
  return remaining || null;
}

/**
 * Create default OSC handlers for speak and media overlay.
 */
export function createDefaultOscHandlers(
  inst: TerminalInstance,
  speakFn?: (text: string) => void,
): OscHandlerEntry[] {
  const handlers: OscHandlerEntry[] = [];

  // TTS: \x1b]9999;speak:<base64>\x07
  handlers.push({
    prefix: "\x1b]9999;speak:",
    handler: (b64: string) => {
      try {
        const text = atob(b64);
        if (speakFn) {
          speakFn(text);
        } else {
          // Browser TTS fallback
          if ("speechSynthesis" in window) {
            const utterance = new SpeechSynthesisUtterance(text);
            speechSynthesis.speak(utterance);
          }
        }
      } catch {
        /* ignore malformed base64 */
      }
    },
  });

  // Media overlay: \x1b]9998;media:<base64>\x07
  handlers.push({
    prefix: "\x1b]9998;media:",
    handler: (b64: string) => {
      try {
        const ref = JSON.parse(atob(b64));
        showMediaOverlay(ref, inst);
      } catch {
        /* ignore malformed */
      }
    },
  });

  return handlers;
}

/* ── Internals ──────────────────────────────────────── */

function extractOsc(
  data: string,
  prefix: string,
  handler: OscCallback,
): string {
  const idx = data.indexOf(prefix);
  if (idx === -1) return data;
  const start = idx + prefix.length;
  const end = data.indexOf("\x07", start);
  if (end === -1) return data;
  handler(data.slice(start, end));
  return data.slice(0, idx) + data.slice(end + 1);
}

function showMediaOverlay(
  ref: { type: string; path: string; url?: string },
  inst: TerminalInstance,
): void {
  const container = inst.terminal?.element?.parentElement;
  if (!container) return;

  const overlay = document.createElement("div");
  overlay.className = "stx-shell-terminal-media-overlay";
  overlay.style.cssText =
    "position:absolute;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.85);display:flex;align-items:center;justify-content:center;z-index:100;";

  const closeBtn = document.createElement("button");
  closeBtn.className = "stx-shell-terminal-media-close";
  closeBtn.innerHTML = "&times;";
  closeBtn.style.cssText =
    "position:absolute;top:8px;right:8px;background:none;border:none;color:#fff;font-size:24px;cursor:pointer;";
  closeBtn.onclick = () => overlay.remove();
  overlay.appendChild(closeBtn);

  const url = ref.url || ref.path;
  if (ref.type === "image") {
    const img = document.createElement("img");
    img.src = url;
    img.style.maxWidth = "100%";
    img.style.maxHeight = "80%";
    overlay.appendChild(img);
  } else {
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.textContent = ref.path.split("/").pop() || ref.path;
    link.style.color = "var(--color-accent-fg, #58a6ff)";
    overlay.appendChild(link);
  }

  container.style.position = "relative";
  container.appendChild(overlay);
  setTimeout(() => overlay.remove(), 15000);
}
