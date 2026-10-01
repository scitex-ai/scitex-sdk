/**
 * SSE Stream Handler for AI Chat.
 *
 * Processes Server-Sent Events from the chat backend.
 * Ported from scitex-cloud's stream-handler.ts.
 *
 * Decoupled from Django — uses ChatAdapter for backend abstraction.
 */

import type { StreamContext, StoredMessage, MediaRef } from "./types";
import { setModelBadge } from "./_model-badge";
import { appendToolTags } from "./_tool-tags";
import { saveMessage } from "./_storage";
import {
  renderMarkdown,
  highlightCodeBlocks,
  fixExternalLinks,
} from "./_markdown-render";

const RENDER_DEBOUNCE_MS = 150;

/** Flush accumulated text buffer as rendered markdown into a container. */
function flushTextBuffer(
  textBuf: string,
  msgEl: HTMLElement,
): HTMLElement | null {
  if (!textBuf.trim()) return null;
  const wrapper = document.createElement("div");
  wrapper.className = "stx-shell-ai-md-segment";
  wrapper.innerHTML = renderMarkdown(textBuf);
  highlightCodeBlocks(wrapper);
  fixExternalLinks(wrapper);
  msgEl.appendChild(wrapper);
  return wrapper;
}

/** Process SSE stream and render assistant response. */
export async function processStream(
  resp: Response,
  msgEl: HTMLElement,
  ctx: StreamContext,
): Promise<void> {
  const toolsUsed: string[] = [];
  const mediaRefs: MediaRef[] = [];
  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // Text accumulator for markdown rendering
  let textBuf = "";
  let previewEl: HTMLElement | null = null;
  let renderTimer: ReturnType<typeof setTimeout> | null = null;

  /** Debounced live preview of accumulated text. */
  function schedulePreview(): void {
    if (renderTimer) clearTimeout(renderTimer);
    renderTimer = setTimeout(() => {
      if (!textBuf.trim()) return;
      if (!previewEl) {
        previewEl = document.createElement("div");
        previewEl.className =
          "stx-shell-ai-md-segment stx-shell-ai-md-streaming";
        msgEl.appendChild(previewEl);
      }
      previewEl.innerHTML = renderMarkdown(textBuf);
      if (ctx.scrollIfNeeded) ctx.scrollIfNeeded();
      else
        requestAnimationFrame(() => {
          ctx.messagesEl.scrollTop = ctx.messagesEl.scrollHeight;
        });
    }, RENDER_DEBOUNCE_MS);
  }

  /** Finalize the current text segment: replace preview with final render. */
  function finalizeTextSegment(): void {
    if (renderTimer) clearTimeout(renderTimer);
    renderTimer = null;
    if (previewEl) {
      previewEl.remove();
      previewEl = null;
    }
    flushTextBuffer(textBuf, msgEl);
    textBuf = "";
  }

  let fullText = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (raw === "[DONE]") break;
      let event: Record<string, unknown>;
      try {
        event = JSON.parse(raw);
      } catch {
        continue;
      }

      if (event.type === "model") {
        setModelBadge(ctx.modelBadge, event.name as string);
      } else if (event.type === "chunk") {
        const chunk = event.text as string;
        textBuf += chunk;
        fullText += chunk;
        schedulePreview();
      } else if (event.type === "tool_start") {
        finalizeTextSegment();
        toolsUsed.push(event.name as string);
        appendToolTags(msgEl, [event.name as string]);
        // Auto-speak from audio_speak tool
        if (event.name === "audio_speak" && event.args) {
          try {
            const a = JSON.parse(event.args as string) as Record<
              string,
              unknown
            >;
            if (a.text) ctx.speak(a.text as string);
          } catch {
            /**/
          }
        }
      } else if (event.type === "file_ops") {
        const ops = event.ops as { path: string; op: string }[];
        if (ops?.length) {
          for (const op of ops) {
            const badge = document.createElement("span");
            badge.className = `stx-shell-ai-file-op stx-shell-ai-file-op--${op.op}`;
            const icon =
              op.op === "created"
                ? "fa-plus-circle"
                : op.op === "modified"
                  ? "fa-pen"
                  : op.op === "moved"
                    ? "fa-arrow-right"
                    : "fa-trash";
            const parts = op.path.split("/");
            const fname = parts.pop() || op.path;
            const dir = parts.length > 0 ? parts.join("/") + "/" : "";
            badge.innerHTML = dir
              ? `<i class="fas ${icon}"></i> <span class="stx-shell-ai-file-op-dir">${dir}</span>${fname}`
              : `<i class="fas ${icon}"></i> ${fname}`;
            msgEl.appendChild(badge);
          }
          if (ctx.scrollIfNeeded) ctx.scrollIfNeeded();
        }
      } else if (event.type === "error") {
        finalizeTextSegment();
        msgEl.remove();
        const errEl = document.createElement("div");
        errEl.className = "stx-shell-ai-msg error";
        ctx.messagesEl.appendChild(errEl);
        errEl.textContent = `AI request failed: ${event.error as string}`;
        saveMessage({ role: "error", text: errEl.textContent });
      }
    }
  }

  // Flush remaining text
  finalizeTextSegment();

  // Dispatch event for file tree refresh (consumers listen)
  const fileTools = [
    "project_write_file",
    "project_exec_python",
    "project_exec_shell",
  ];
  if (toolsUsed.some((t) => fileTools.includes(t))) {
    document.dispatchEvent(
      new CustomEvent("stx-shell:files-changed", {
        detail: { toolsUsed },
      }),
    );
  }

  // Save and optionally speak
  if (fullText || toolsUsed.length > 0 || mediaRefs.length > 0) {
    saveMessage({
      role: "assistant",
      text: fullText,
      toolsUsed,
      media: mediaRefs.length > 0 ? mediaRefs : undefined,
    } as StoredMessage);
    if (fullText && ctx.autoSpeak && !toolsUsed.includes("audio_speak")) {
      ctx.speak(fullText);
    }
  }
}
