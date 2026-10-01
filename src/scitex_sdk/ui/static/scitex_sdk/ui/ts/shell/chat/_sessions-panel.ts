/**
 * Sessions Panel for AI Chat — ported from scitex-cloud.
 *
 * Manages chat sessions: list, create, rename, delete, switch.
 * Renders as a horizontal bar of session chips above the messages area.
 *
 * Uses SessionAdapter interface so scitex-ui has no hardcoded URLs —
 * the consuming app (figrecipe, scitex-cloud) provides the adapter.
 */

// ---------------------------------------------------------------------------
// Adapter interface — implemented by consuming app
// ---------------------------------------------------------------------------

export interface SessionAdapter {
  listSessions(): Promise<
    { id: number; title: string; updated_at: string; message_count?: number }[]
  >;
  getMessages(
    sessionId: number,
  ): Promise<{ session_id: number; title: string; messages: SessionMessage[] }>;
  createSession(title?: string): Promise<{ id: number; title: string }>;
  deleteSession(sessionId: number): Promise<void>;
  addMessage(sessionId: number, role: string, content: string): Promise<void>;
  renameSession?(sessionId: number, title: string): Promise<void>;
}

export interface SessionMessage {
  id?: number;
  role: "user" | "assistant" | "error";
  content: string;
}

// ---------------------------------------------------------------------------
// SessionsPanel
// ---------------------------------------------------------------------------

export class SessionsPanel {
  currentSessionId: number | null = null;
  private sessions: Array<{
    id: number;
    title: string;
    updated_at: string;
    message_count?: number;
  }> = [];
  private listEl: HTMLElement | null = null;
  private chatCounter = 0;
  private contextMenu: HTMLElement | null = null;
  private adapter: SessionAdapter | null = null;

  private onSwitch:
    | ((messages: SessionMessage[], sessionId: number) => void)
    | null = null;
  private onClear: (() => void) | null = null;

  /**
   * Initialise the sessions panel.
   *
   * @param listEl  Container element for the session chips.
   * @param adapter Backend adapter (no hardcoded URLs).
   * @param onSwitch Called when user switches session — receives messages.
   * @param onClear  Called when user clicks "New Chat" (clear messages area).
   */
  init(
    listEl: HTMLElement,
    adapter: SessionAdapter,
    onSwitch: (messages: SessionMessage[], sessionId: number) => void,
    onClear: () => void,
  ): void {
    this.listEl = listEl;
    this.adapter = adapter;
    this.onSwitch = onSwitch;
    this.onClear = onClear;

    // New chat button
    const newBtn = document.querySelector<HTMLButtonElement>(
      ".stx-shell-ai-new-chat",
    );
    newBtn?.addEventListener("click", () => this.newChat());

    // Restore last session from sessionStorage
    const saved = sessionStorage.getItem("scitex_ai_session_id");
    if (saved) this.currentSessionId = parseInt(saved, 10);

    // Dismiss context menu on click-outside
    document.addEventListener("click", () => this.dismissContextMenu());

    void this.loadSessions();
  }

  // -----------------------------------------------------------------------
  // Public API
  // -----------------------------------------------------------------------

  async loadSessions(): Promise<void> {
    if (!this.adapter) return;
    try {
      const sessions = await this.adapter.listSessions();
      this.sessions = sessions;
      // Auto-select first session if none is active
      if (!this.currentSessionId && sessions.length > 0) {
        this.currentSessionId = sessions[0].id;
        sessionStorage.setItem("scitex_ai_session_id", String(sessions[0].id));
      }
      this.render(sessions);
      // Auto-create C1 if no sessions exist
      if (sessions.length === 0) {
        await this.createSession("C1");
      }
    } catch (err) {
      console.error("[SessionsPanel] loadSessions failed:", err);
    }
  }

  async createSession(title?: string): Promise<number | null> {
    if (!this.adapter) return null;
    try {
      const session = await this.adapter.createSession(
        title || `C${this.chatCounter + 1}`,
      );
      this.currentSessionId = session.id;
      sessionStorage.setItem("scitex_ai_session_id", String(session.id));
      void this.loadSessions();
      return session.id;
    } catch (err) {
      console.error("[SessionsPanel] createSession failed:", err);
      return null;
    }
  }

  async switchSession(id: number): Promise<void> {
    if (!this.adapter) return;
    try {
      const data = await this.adapter.getMessages(id);
      this.currentSessionId = id;
      sessionStorage.setItem("scitex_ai_session_id", String(id));
      this.onSwitch?.(data.messages, id);
      this.highlightActive();
    } catch (err) {
      console.error("[SessionsPanel] switchSession failed:", err);
    }
  }

  async saveMessage(role: string, content: string): Promise<void> {
    if (!this.currentSessionId || !this.adapter) return;
    try {
      await this.adapter.addMessage(this.currentSessionId, role, content);
      // Refresh session list to update titles / counts
      void this.loadSessions();
    } catch (err) {
      console.error("[SessionsPanel] saveMessage failed:", err);
    }
  }

  newChat(): void {
    this.currentSessionId = null;
    sessionStorage.removeItem("scitex_ai_session_id");
    this.onClear?.();
    this.highlightActive();
  }

  getSessionId(): number | null {
    return this.currentSessionId;
  }

  // -----------------------------------------------------------------------
  // Rendering
  // -----------------------------------------------------------------------

  private render(
    sessions: Array<{
      id: number;
      title: string;
      updated_at: string;
      message_count?: number;
    }>,
  ): void {
    if (!this.listEl) return;
    this.listEl.innerHTML = "";

    this.chatCounter = sessions.length;

    for (const s of sessions) {
      const chip = document.createElement("div");
      chip.className = "stx-shell-ai-session-item";
      if (s.id === this.currentSessionId) chip.classList.add("active");
      chip.dataset.sessionId = String(s.id);

      const title = document.createElement("span");
      title.className = "stx-shell-ai-session-title";
      title.textContent = s.title;
      title.addEventListener("dblclick", (e) => {
        e.stopPropagation();
        this.startRename(chip, s.id, s.title);
      });

      const del = document.createElement("button");
      del.className = "stx-shell-ai-session-del";
      del.innerHTML = '<i class="fas fa-times"></i>';
      del.title = "Delete";
      del.addEventListener("click", (e) => {
        e.stopPropagation();
        void this.deleteSession(s.id);
      });

      chip.appendChild(title);
      chip.appendChild(del);
      chip.addEventListener("click", () => void this.switchSession(s.id));

      // Right-click context menu
      chip.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.showContextMenu(e, s);
      });

      this.listEl.appendChild(chip);
    }
  }

  // -----------------------------------------------------------------------
  // Context menu
  // -----------------------------------------------------------------------

  private showContextMenu(
    e: MouseEvent,
    s: { id: number; title: string },
  ): void {
    this.dismissContextMenu();

    const menu = document.createElement("div");
    menu.className = "stx-shell-ai-context-menu";
    menu.style.left = `${e.clientX}px`;
    menu.style.top = `${e.clientY}px`;

    const items: Array<{ label: string; icon: string; action: () => void }> = [
      {
        label: "Rename",
        icon: "fas fa-pen",
        action: () => {
          const chip = this.listEl?.querySelector(
            `[data-session-id="${s.id}"]`,
          ) as HTMLElement;
          if (chip) this.startRename(chip, s.id, s.title);
        },
      },
      {
        label: "Delete",
        icon: "fas fa-trash",
        action: () => void this.deleteSession(s.id),
      },
    ];

    for (const item of items) {
      const el = document.createElement("div");
      el.className = "stx-shell-ai-context-menu-item";
      el.innerHTML = `<i class="${item.icon}"></i> ${item.label}`;
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        this.dismissContextMenu();
        item.action();
      });
      menu.appendChild(el);
    }

    document.body.appendChild(menu);
    this.contextMenu = menu;
  }

  private dismissContextMenu(): void {
    if (this.contextMenu) {
      this.contextMenu.remove();
      this.contextMenu = null;
    }
  }

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------

  private highlightActive(): void {
    if (!this.listEl) return;
    for (const el of this.listEl.querySelectorAll(
      ".stx-shell-ai-session-item",
    )) {
      const id = parseInt((el as HTMLElement).dataset.sessionId || "0", 10);
      el.classList.toggle("active", id === this.currentSessionId);
    }
  }

  private startRename(chip: HTMLElement, id: number, current: string): void {
    const titleEl = chip.querySelector(".stx-shell-ai-session-title");
    if (!titleEl) return;

    const input = document.createElement("input");
    input.className = "stx-shell-ai-session-rename";
    input.value = current;
    titleEl.replaceWith(input);
    input.focus();
    input.select();

    const finish = async () => {
      const val = input.value.trim() || current;
      input.replaceWith(titleEl);
      titleEl.textContent = val;
      if (val !== current && this.adapter?.renameSession) {
        try {
          await this.adapter.renameSession(id, val);
        } catch (err) {
          console.error("[SessionsPanel] rename failed:", err);
        }
      }
    };

    input.addEventListener("blur", () => void finish());
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        input.blur();
      } else if (e.key === "Escape") {
        input.value = current;
        input.blur();
      }
    });
  }

  private async deleteSession(id: number): Promise<void> {
    if (!this.adapter) return;
    try {
      await this.adapter.deleteSession(id);
      if (this.currentSessionId === id) this.newChat();
      void this.loadSessions();
    } catch (err) {
      console.error("[SessionsPanel] deleteSession failed:", err);
    }
  }
}
