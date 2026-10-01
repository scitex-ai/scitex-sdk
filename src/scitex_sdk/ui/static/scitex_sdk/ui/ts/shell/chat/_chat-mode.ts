/**
 * ChatMode — reusable AI chat orchestration class.
 *
 * Ported from scitex-cloud's AIPanelChatMode (chat-mode.ts, 512 lines).
 * Decoupled from Django — uses ChatAdapter for backend abstraction.
 *
 * Handles:
 *   - Enter-to-send from textarea
 *   - SSE streaming with tool events (via _chat-send.ts + _stream-handler.ts)
 *   - Markdown rendering via _markdown-render.ts
 *   - Tool badge rendering via _tool-tags.ts
 *   - Message persistence via _storage.ts
 *   - Input history via _history.ts (C-p / C-n)
 *   - Auto-scroll (MutationObserver + scroll tracking)
 *   - Image attachments (paste, file picker)
 *   - Textarea auto-resize
 *   - Clear chat / copy / print
 */

import type { ChatAdapter, AiContext } from "./types";
import type { SessionsPanel } from "./_sessions-panel";
import { clearMessages, loadMessages, saveMessage } from "./_storage";
import { loadHistory, pushHistory } from "./_history";
import {
  renderMarkdown,
  highlightCodeBlocks,
  fixExternalLinks,
} from "./_markdown-render";
import { appendToolTags } from "./_tool-tags";
import { ImageInputManager } from "./_image-input";
import { SketchCanvas } from "./_sketch-canvas";
import { WebcamCapture } from "./_webcam-capture";
import { VoiceRecorder } from "./_recorder";
import type { SttAdapter } from "./_recorder";
import { speakText } from "./_speech";
import type { TtsAdapter } from "./_speech";
import { chatSend } from "./_chat-send";

/* ── Public interfaces ──────────────────────────────────────────── */

export interface ChatModeRefs {
  messagesEl: HTMLElement | null;
  inputEl: HTMLTextAreaElement | null;
  sendBtn: HTMLButtonElement | null;
  speakBtn: HTMLButtonElement | null;
  micBtn: HTMLButtonElement | null;
  sttModelSelect: HTMLSelectElement | null;
  modelBadge: HTMLElement | null;
  volBars: HTMLElement[];
  imagePreviewEl: HTMLElement | null;
  imageFileInput: HTMLInputElement | null;
  cameraBtn: HTMLButtonElement | null;
  sketchBtn: HTMLButtonElement | null;
}

export interface ChatModeOptions {
  adapter: ChatAdapter;
  sttAdapter?: SttAdapter;
  ttsAdapter?: TtsAdapter;
  autoSpeak?: boolean;
  emptyStateHtml?: string;
}

/* ── Default empty state ────────────────────────────────────────── */

const DEFAULT_EMPTY_HTML = `
  <div class="stx-shell-ai-empty">
    <i class="fas fa-robot"></i>
    <span>Ask anything about SciTeX.</span>
    <span>I can take actions: stats, plots, literature, and your current work.</span>
  </div>`;

/* ── ChatMode class ─────────────────────────────────────────────── */

export class ChatMode {
  /* DOM refs */
  private messagesEl: HTMLElement | null = null;
  private inputEl: HTMLTextAreaElement | null = null;
  private sendBtn: HTMLButtonElement | null = null;
  private speakBtn: HTMLButtonElement | null = null;
  private micBtn: HTMLButtonElement | null = null;
  private sttModelSelect: HTMLSelectElement | null = null;
  private modelBadge: HTMLElement | null = null;

  /* Adapters */
  private adapter!: ChatAdapter;
  private sttAdapter: SttAdapter | undefined;
  private ttsAdapter: TtsAdapter | undefined;

  /* State */
  private busy = false;
  private autoSpeak = false;
  private currentAudio: HTMLAudioElement | null = null;
  private recorder: VoiceRecorder | null = null;
  private imageInput: ImageInputManager | null = null;
  private sketchCanvas: SketchCanvas | null = null;
  private webcamCapture: WebcamCapture | null = null;

  /* Input history (C-p / C-n) */
  private history: string[] = [];
  private historyIdx = -1;
  private historyDraft = "";

  /* Context — mutated externally via setContext() */
  private context: AiContext = {};

  /* Sessions panel — set externally for server-side session persistence */
  private sessionsPanel: SessionsPanel | null = null;

  /* Auto-scroll: true when user is at/near bottom */
  private _userAtBottom = true;

  /* Customisation */
  private emptyStateHtml = DEFAULT_EMPTY_HTML;

  /* ── Init ──────────────────────────────────────────────────── */

  init(refs: ChatModeRefs, opts: ChatModeOptions, context?: AiContext): void {
    /* Store refs */
    this.messagesEl = refs.messagesEl;
    this.inputEl = refs.inputEl;
    this.sendBtn = refs.sendBtn;
    this.speakBtn = refs.speakBtn;
    this.micBtn = refs.micBtn;
    this.sttModelSelect = refs.sttModelSelect;
    this.modelBadge = refs.modelBadge;

    /* Store options */
    this.adapter = opts.adapter;
    this.sttAdapter = opts.sttAdapter;
    this.ttsAdapter = opts.ttsAdapter;
    this.autoSpeak = opts.autoSpeak ?? false;
    if (opts.emptyStateHtml !== undefined) {
      this.emptyStateHtml = opts.emptyStateHtml;
    }

    /* Context */
    if (context) this.context = context;

    /* Recorder + mic button click */
    this.recorder = new VoiceRecorder(refs.volBars, this.micBtn);
    this.micBtn?.addEventListener("click", () => this.toggleRecording());

    /* History */
    this.history = loadHistory();

    /* Image, webcam, sketch support */
    // Gated on the PREVIEW element only. A template that ships no
    // `<input type="file">` used to lose the camera, the sketch pad and paste
    // as well — three features that do not need a picker, switched off by the
    // absence of one. Both collaborators synthesise their own now.
    if (refs.imagePreviewEl) {
      this.imageInput = new ImageInputManager(
        refs.imagePreviewEl,
        refs.imageFileInput,
      );
      if (this.inputEl) this.imageInput.bindPaste(this.inputEl);
      this.sketchCanvas = new SketchCanvas(this.imageInput);
      this.webcamCapture = new WebcamCapture(
        this.imageInput,
        refs.imageFileInput,
      );
      refs.cameraBtn?.addEventListener(
        "click",
        () => void this.webcamCapture?.open(),
      );
      refs.sketchBtn?.addEventListener("click", () =>
        this.sketchCanvas?.open(),
      );
    }

    /* Track user scroll position — auto-scroll only when at bottom */
    this.messagesEl?.addEventListener("scroll", () => {
      if (!this.messagesEl) return;
      const el = this.messagesEl;
      this._userAtBottom =
        el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    });

    /* MutationObserver: auto-scroll when new content is added */
    if (this.messagesEl) {
      const el = this.messagesEl;
      const mo = new MutationObserver(() => {
        if (!this._userAtBottom) return;
        el.scrollTop = 999999;
      });
      mo.observe(el, { childList: true, subtree: true });
    }
  }

  /* ── Scroll helpers ────────────────────────────────────────── */

  scrollToBottomIfNeeded(): void {
    if (!this.messagesEl) return;
    this.messagesEl.scrollTop = 999999;
  }

  scrollToBottom(): void {
    if (!this.messagesEl) return;
    this._userAtBottom = true;
    this.messagesEl.scrollTop = 999999;
  }

  /* ── Context ───────────────────────────────────────────────── */

  setContext(context: AiContext): void {
    this.context = context;
  }

  getContext(): AiContext {
    return this.context;
  }

  /** Wire a SessionsPanel for server-side session persistence. */
  setSessionsPanel(sp: SessionsPanel): void {
    this.sessionsPanel = sp;
  }

  /* ── Clear / Restore / Copy / Print ────────────────────────── */

  clearChat(): void {
    this.clearConversation();
  }

  clearConversation(): void {
    clearMessages();
    if (this.messagesEl) {
      this.messagesEl.innerHTML = this.emptyStateHtml;
    }
  }

  restoreConversation(): void {
    const stored = loadMessages();
    if (stored.length === 0 || !this.messagesEl) return;
    this.messagesEl.innerHTML = "";
    for (const msg of stored) {
      const el = this.createMsgEl(msg.role);
      if (msg.role === "assistant" && msg.text) {
        const wrapper = document.createElement("div");
        wrapper.className = "stx-shell-ai-md-segment";
        wrapper.innerHTML = renderMarkdown(msg.text);
        highlightCodeBlocks(wrapper);
        fixExternalLinks(wrapper);
        el.appendChild(wrapper);
      } else {
        el.appendChild(document.createTextNode(msg.text));
      }
      if (msg.toolsUsed?.length) appendToolTags(el, msg.toolsUsed);
    }
    this.scrollToBottom();
    this._scrollRepeatedlyForLayout();
  }

  /** Load messages from a session (server-side sessions). */
  loadSessionMessages(
    messages: Array<{
      role: "user" | "assistant" | "error";
      text: string;
      tools_used: string[];
      media: Array<{ type: string; path: string; ext: string }>;
    }>,
  ): void {
    if (!this.messagesEl) return;
    this.messagesEl.innerHTML = "";
    for (const msg of messages) {
      const el = this.createMsgEl(msg.role);
      if (msg.role === "assistant" && msg.text) {
        const wrapper = document.createElement("div");
        wrapper.className = "stx-shell-ai-md-segment";
        wrapper.innerHTML = renderMarkdown(msg.text);
        highlightCodeBlocks(wrapper);
        fixExternalLinks(wrapper);
        el.appendChild(wrapper);
      } else {
        el.appendChild(document.createTextNode(msg.text));
      }
      if (msg.tools_used?.length) appendToolTags(el, msg.tools_used);
    }
    this.scrollToBottom();
    this._scrollRepeatedlyForLayout();
  }

  async copyChat(): Promise<void> {
    if (!this.messagesEl) return;
    const msgs = this.messagesEl.querySelectorAll(".stx-shell-ai-msg");
    const lines: string[] = [];
    msgs.forEach((el) => {
      const role = el.classList.contains("user") ? "You" : "AI";
      lines.push(`${role}: ${(el as HTMLElement).innerText.trim()}`);
    });
    const text = lines.join("\n\n");
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* clipboard not available */
    }
  }

  printChat(): void {
    if (!this.messagesEl) return;
    document.body.classList.add("scitex-print-chat");
    window.print();
    document.body.classList.remove("scitex-print-chat");
  }

  /* ── Message element creation ──────────────────────────────── */

  createMsgEl(role: "user" | "assistant" | "error"): HTMLElement {
    const el = document.createElement("div");
    el.className = `stx-shell-ai-msg ${role}`;
    this.messagesEl?.appendChild(el);
    this.scrollToBottomIfNeeded();
    return el;
  }

  /* ── History navigation (C-p / C-n) ────────────────────────── */

  navigateHistory(delta: -1 | 1): void {
    if (!this.inputEl || this.history.length === 0) return;
    if (this.historyIdx === -1) this.historyDraft = this.inputEl.value;
    const next = this.historyIdx + delta;
    if (next < -1 || next >= this.history.length) return;
    this.historyIdx = next;
    this.inputEl.value = next === -1 ? this.historyDraft : this.history[next];
    this.inputEl.dispatchEvent(new Event("input"));
    const len = this.inputEl.value.length;
    this.inputEl.setSelectionRange(len, len);
  }

  /* ── Page hints (data-ai-hint attributes) ──────────────────── */

  collectPageHints(): string[] {
    const hints: string[] = [];
    document.querySelectorAll<HTMLElement>("[data-ai-hint]").forEach((el) => {
      const hint = el.dataset.aiHint;
      if (hint) hints.push(hint);
    });
    const viewerSidebar = document.getElementById("ws-viewer-sidebar");
    const activeFile = viewerSidebar?.dataset.aiViewerActive;
    if (activeFile) {
      hints.push(`Currently open in editor: ${activeFile}`);
    }
    return hints;
  }

  /* ── Send ───────────────────────────────────────────────────── */

  async send(): Promise<void> {
    if (this.busy || !this.inputEl || !this.messagesEl) return;
    const prompt = this.inputEl.value.trim();
    if (!prompt) return;

    this.history = pushHistory(this.history, prompt);
    this.historyIdx = -1;

    /* Chat commands */
    if (prompt === "/clear") {
      this.clearChat();
      this.inputEl.value = "";
      return;
    }

    this.currentAudio?.pause();
    this.currentAudio = null;
    this.messagesEl.querySelector(".stx-shell-ai-empty")?.remove();

    /* User is actively chatting — always scroll to bottom */
    this._userAtBottom = true;

    const userEl = this.createMsgEl("user");
    userEl.textContent = prompt;
    this.imageInput?.renderInlineThumbsInto(userEl);
    saveMessage({ role: "user", text: prompt });
    void this.sessionsPanel?.saveMessage("user", prompt);

    /* Collect image attachments before clearing */
    const images = this.imageInput?.hasAttachments()
      ? this.imageInput.getAttachmentsAsBase64()
      : [];
    this.imageInput?.clearAttachments();

    this.inputEl.value = "";
    this.inputEl.style.height = "auto";

    this.busy = true;
    if (this.sendBtn) this.sendBtn.disabled = true;

    /* Merge page hints into context */
    this.context.page_hints = this.collectPageHints();

    try {
      await chatSend({
        prompt,
        adapter: this.adapter,
        context: this.context,
        images,
        messagesEl: this.messagesEl,
        modelBadge: this.modelBadge,
        autoSpeak: this.autoSpeak,
        speak: (t) => void this.speak(t),
        scrollIfNeeded: () => this.scrollToBottomIfNeeded(),
        createMsgEl: (role) => this.createMsgEl(role),
        onAssistantDone: (_msgEl, text) => {
          this.scrollToBottom();
          setTimeout(() => this.scrollToBottom(), 200);
          setTimeout(() => this.scrollToBottom(), 500);
          if (text) void this.sessionsPanel?.saveMessage("assistant", text);
        },
      });
    } finally {
      this.busy = false;
      if (this.sendBtn) this.sendBtn.disabled = false;
    }
  }

  /* ── Speak / TTS ───────────────────────────────────────────── */

  async speak(text: string): Promise<void> {
    this.currentAudio?.pause();
    this.currentAudio = null;
    this.currentAudio = await speakText(text, this.ttsAdapter);
  }

  toggleSpeak(): void {
    this.autoSpeak = !this.autoSpeak;
    this.speakBtn?.classList.toggle("active", this.autoSpeak);
    if (!this.autoSpeak) {
      this.currentAudio?.pause();
      this.currentAudio = null;
    }
  }

  get isAutoSpeak(): boolean {
    return this.autoSpeak;
  }

  /* ── Mic / Recording ───────────────────────────────────────── */

  toggleRecording(): void {
    if (!this.recorder || !this.sttAdapter) return;
    if (this.recorder.isRecording) {
      this.recorder.stop();
    } else {
      void this.recorder.start(
        this.sttAdapter,
        (text) => {
          if (!this.inputEl) return;
          const cur = this.inputEl.value.trim();
          this.inputEl.value = cur ? `${cur} ${text}` : text;
          this.inputEl.dispatchEvent(new Event("input"));
          this.inputEl.focus();
        },
        () => this.sttModelSelect?.value ?? "",
      );
    }
  }

  /* ── Busy state (read-only) ────────────────────────────────── */

  get isBusy(): boolean {
    return this.busy;
  }

  /* ── Private helpers ───────────────────────────────────────── */

  /**
   * Repeatedly scroll to bottom over 3 seconds.
   * Handles images loading and layout shifts after restore.
   */
  private _scrollRepeatedlyForLayout(): void {
    const iv = setInterval(() => {
      if (this.messagesEl) this.messagesEl.scrollTop = 999999;
    }, 100);
    setTimeout(() => clearInterval(iv), 3000);
  }
}
