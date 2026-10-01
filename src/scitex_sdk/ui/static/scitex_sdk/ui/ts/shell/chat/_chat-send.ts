/**
 * Chat SSE send — fetch + event parsing for AI chat.
 *
 * Ported from scitex-cloud's chat-mode.ts (send logic).
 * Decoupled from Django — uses ChatAdapter.streamChat() for the fetch.
 *
 * Handles: response error extraction, typing indicator lifecycle,
 * and delegates SSE event processing to _stream-handler.ts.
 */

import type { ChatAdapter, AiContext, StreamContext } from "./types";
import { processStream } from "./_stream-handler";
import { saveMessage } from "./_storage";

export interface SendOptions {
  prompt: string;
  adapter: ChatAdapter;
  context: AiContext;
  images: { mime: string; base64: string }[];
  messagesEl: HTMLElement;
  modelBadge: HTMLElement | null;
  autoSpeak: boolean;
  speak: (text: string) => void;
  scrollIfNeeded: () => void;
  createMsgEl: (role: "user" | "assistant" | "error") => HTMLElement;
  /** Called after a successful assistant response with the message element. */
  onAssistantDone?: (msgEl: HTMLElement, text: string) => void;
}

/**
 * Execute a chat send: POST via adapter, handle errors, stream response.
 *
 * The caller is responsible for:
 *   - creating the user message element
 *   - managing busy state
 *   - creating/removing the typing indicator
 *
 * This function creates the typing indicator, sends the request,
 * removes the indicator, and streams the response.
 */
export async function chatSend(opts: SendOptions): Promise<void> {
  const {
    prompt,
    adapter,
    context,
    images,
    messagesEl,
    modelBadge,
    autoSpeak,
    speak,
    scrollIfNeeded,
    createMsgEl,
    onAssistantDone,
  } = opts;

  // Typing indicator
  const typing = document.createElement("div");
  typing.className = "stx-shell-ai-typing";
  typing.textContent = "Thinking";
  messagesEl.appendChild(typing);

  try {
    const imageStrs =
      images.length > 0 ? images.map((i) => i.base64) : undefined;
    const resp = await adapter.streamChat(prompt, context, imageStrs);

    if (!resp.ok || !resp.body) {
      typing.remove();
      const errEl = createMsgEl("error");
      try {
        const data = (await resp.json()) as {
          error?: string;
          settings_url?: string;
        };
        const msg = data.error ?? `Request failed: ${resp.status}`;
        if (data.settings_url) {
          errEl.textContent = msg + " ";
          const link = document.createElement("a");
          link.href = data.settings_url;
          link.textContent = "Go to Settings > AI Providers";
          link.style.color = "inherit";
          link.style.textDecoration = "underline";
          errEl.appendChild(link);
        } else {
          errEl.textContent = msg;
        }
      } catch {
        errEl.textContent = `Request failed: ${resp.status}`;
      }
      saveMessage({ role: "error", text: errEl.textContent ?? "" });
      return;
    }

    typing.remove();
    const msgEl = createMsgEl("assistant");
    const streamCtx: StreamContext = {
      messagesEl,
      modelBadge,
      speak,
      autoSpeak,
      scrollIfNeeded,
    };
    await processStream(resp, msgEl, streamCtx);

    if (onAssistantDone) {
      onAssistantDone(msgEl, msgEl.textContent ?? "");
    }
  } catch (err) {
    typing.remove();
    const errEl = createMsgEl("error");
    errEl.textContent = `Network error: ${err}`;
    saveMessage({ role: "error", text: errEl.textContent });
  }
}
