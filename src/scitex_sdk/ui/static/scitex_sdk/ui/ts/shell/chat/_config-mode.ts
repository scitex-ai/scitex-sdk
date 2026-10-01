/**
 * Config Mode — Settings popover for the AI chat shell.
 *
 * Renders skills/tool toggles as a floating popover above the toolbar.
 * Ported from scitex-cloud's config-mode.ts with ConfigAdapter for
 * backend abstraction. Uses proper CSS classes (ai-config-*) matching
 * scitex-cloud's design exactly.
 */

/** Adapter for loading/saving config data. */
export interface ConfigAdapter {
  /** Fetch MCP tool groups with enabled states. */
  fetchMcpPrefs?(): Promise<McpPrefsGroup[]>;
  /** Save MCP preferences. */
  saveMcpPrefs?(prefs: Record<string, boolean>): Promise<void>;
  /** Fetch skills info. */
  fetchSkills?(): Promise<Record<string, SkillInfo>>;
}

export interface McpPrefsGroup {
  name: string;
  display: string;
  icon: string;
  desc: string;
  enabled: boolean;
  tool_count: number;
}

export interface SkillInfo {
  name: string;
  description: string;
  icon?: string;
  enabled?: boolean;
}

export class ConfigMode {
  private adapter: ConfigAdapter;
  private saveTimer: ReturnType<typeof setTimeout> | null = null;
  private popover: HTMLElement | null = null;

  constructor(adapter: ConfigAdapter = {}) {
    this.adapter = adapter;
  }

  /**
   * Create and toggle a config popover anchored to the toolbar.
   * Call this from the settings button click handler.
   */
  toggle(toolbar: HTMLElement): void {
    // If popover exists, toggle visibility
    if (this.popover) {
      const visible = this.popover.style.display !== "none";
      this.popover.style.display = visible ? "none" : "block";
      return;
    }

    // Create popover container
    this.popover = document.createElement("div");
    this.popover.id = "stx-shell-ai-config-popover";
    this.popover.className = "stx-shell-ai-config-popover";
    this.popover.style.display = "block";

    // Toast element (hidden by default, opacity: 0 via CSS)
    const toast = document.createElement("div");
    toast.id = "ai-config-toast";
    toast.className = "ai-config-toast";
    toast.textContent = "Saved";
    this.popover.appendChild(toast);

    // Loading state
    this.popover.innerHTML +=
      '<div style="padding:12px;text-align:center;font-size:11px;color:var(--fg-muted,#8b949e);">Loading...</div>';

    // Anchor to toolbar (position: relative needed on toolbar parent)
    toolbar.style.position = "relative";
    toolbar.appendChild(this.popover);

    // Populate asynchronously
    this.populate(this.popover);

    // Close on outside click
    const closeHandler = (e: MouseEvent) => {
      if (
        this.popover &&
        !this.popover.contains(e.target as Node) &&
        !(e.target as HTMLElement).closest(".stx-shell-ai-gear-btn")
      ) {
        this.popover.style.display = "none";
        document.removeEventListener("mousedown", closeHandler);
      }
    };
    // Defer so the current click doesn't close it immediately
    setTimeout(() => document.addEventListener("mousedown", closeHandler), 0);
  }

  /** Populate the config popover with content. */
  async populate(container: HTMLElement): Promise<void> {
    try {
      let html = "";

      // Skills section
      if (this.adapter.fetchSkills) {
        const skills = await this.adapter.fetchSkills();
        html += this.renderSkills(skills);
      }

      // MCP Tools section
      if (this.adapter.fetchMcpPrefs) {
        const groups = await this.adapter.fetchMcpPrefs();
        html += this.renderMcpGroups(groups);
      }

      if (!html) {
        html =
          '<div class="stx-shell-config-empty">No configuration available</div>';
      }

      // Preserve toast, replace loading content
      const toast = container.querySelector(".ai-config-toast");
      container.innerHTML = html;
      if (toast) container.appendChild(toast);
      else {
        const t = document.createElement("div");
        t.id = "ai-config-toast";
        t.className = "ai-config-toast";
        t.textContent = "Saved";
        container.appendChild(t);
      }

      this.bindCategoryHeaders(container);
      this.bindSkillToggles(container);
      this.bindMcpToggles(container);
    } catch (err) {
      container.innerHTML = `<div class="stx-shell-config-empty"><i class="fas fa-exclamation-triangle"></i> Failed to load config: ${err instanceof Error ? err.message : "unknown"}</div>`;
    }
  }

  /* ── Renderers ───────────────────────────────── */

  private renderSkills(skills: Record<string, SkillInfo>): string {
    const entries = Object.entries(skills);
    if (entries.length === 0) return "";
    const onCount = entries.filter(([, s]) => s.enabled !== false).length;

    let html = `<div class="ai-config-category expanded" data-cat="Skills">`;
    html += `<div class="ai-config-category-header">`;
    html += `<i class="fas fa-chevron-right ai-config-category-chevron"></i>`;
    html += `<span class="ai-config-category-name">Skills</span>`;
    html += `<span class="ai-config-category-count">${onCount}/${entries.length}</span>`;
    html += `</div><div class="ai-config-grid">`;

    for (const [name, skill] of entries) {
      const enabled = skill.enabled !== false;
      const cls = enabled ? "enabled" : "";
      html += `<div class="ai-config-skill" data-skill="${name}">`;
      html += `<div class="ai-config-card ${cls}">`;
      html += `<i class="fas ${skill.icon || "fa-bolt"} ai-config-card-icon"></i>`;
      html += `<div class="ai-config-card-info">`;
      html += `<div class="ai-config-card-name">${skill.name || name}</div>`;
      html += `<div class="ai-config-card-desc">${skill.description || ""}</div>`;
      html += `</div>`;
      html += `<label class="ai-config-toggle" onclick="event.stopPropagation()">`;
      html += `<input type="checkbox" ${enabled ? "checked" : ""} />`;
      html += `<span class="ai-config-slider"></span>`;
      html += `</label></div></div>`;
    }

    html += `</div></div>`;
    return html;
  }

  private renderMcpGroups(groups: McpPrefsGroup[]): string {
    if (groups.length === 0) return "";
    const onCount = groups.filter((g) => g.enabled).length;

    let html = `<div class="ai-config-category" data-cat="MCP Tools">`;
    html += `<div class="ai-config-category-header">`;
    html += `<i class="fas fa-chevron-right ai-config-category-chevron"></i>`;
    html += `<span class="ai-config-category-name">MCP Tools</span>`;
    html += `<span class="ai-config-category-count">${onCount}/${groups.length} enabled</span>`;
    html += `</div><div class="ai-config-grid">`;

    for (const g of groups) {
      const cls = g.enabled ? "enabled" : "";
      html += `<div class="ai-config-module" data-group="${g.name}">`;
      html += `<div class="ai-config-card ${cls}">`;
      html += `<i class="fas ${g.icon || "fa-puzzle-piece"} ai-config-card-icon"></i>`;
      html += `<div class="ai-config-card-info">`;
      html += `<div class="ai-config-card-name">${g.display || g.name}</div>`;
      html += `<div class="ai-config-card-desc">${g.desc || ""} (${g.tool_count} tools)</div>`;
      html += `</div>`;
      html += `<span class="ai-config-card-badge">${g.tool_count}</span>`;
      html += `<label class="ai-config-toggle" onclick="event.stopPropagation()">`;
      html += `<input type="checkbox" ${g.enabled ? "checked" : ""} />`;
      html += `<span class="ai-config-slider"></span>`;
      html += `</label></div></div>`;
    }

    html += `</div></div>`;
    return html;
  }

  /* ── Interaction Bindings ─────────────────────── */

  private bindCategoryHeaders(container: HTMLElement): void {
    container
      .querySelectorAll<HTMLElement>(".ai-config-category-header")
      .forEach((header) => {
        header.addEventListener("click", () => {
          header.closest(".ai-config-category")?.classList.toggle("expanded");
        });
      });
  }

  private bindSkillToggles(container: HTMLElement): void {
    container
      .querySelectorAll<HTMLElement>(".ai-config-skill")
      .forEach((mod) => {
        const cb = mod.querySelector<HTMLInputElement>(
          'input[type="checkbox"]',
        );
        if (!cb) return;
        cb.addEventListener("change", () => {
          mod
            .querySelector(".ai-config-card")
            ?.classList.toggle("enabled", cb.checked);
          // Update count badge
          const cat = mod.closest(".ai-config-category");
          if (cat) {
            const on = cat.querySelectorAll(
              ".ai-config-skill .ai-config-card.enabled",
            ).length;
            const total = cat.querySelectorAll(".ai-config-skill").length;
            const badge = cat.querySelector(".ai-config-category-count");
            if (badge) badge.textContent = `${on}/${total}`;
          }
          this.saveSkillPrefs(container);
          this.showToast();
        });
      });
  }

  private bindMcpToggles(container: HTMLElement): void {
    container
      .querySelectorAll<HTMLElement>(".ai-config-module")
      .forEach((mod) => {
        const cb = mod.querySelector<HTMLInputElement>(
          'input[type="checkbox"]',
        );
        if (!cb) return;
        cb.addEventListener("change", () => {
          mod
            .querySelector(".ai-config-card")
            ?.classList.toggle("enabled", cb.checked);
          const cat = mod.closest(".ai-config-category");
          if (cat) {
            const total = cat.querySelectorAll(".ai-config-module").length;
            const on = cat.querySelectorAll(
              ".ai-config-module .ai-config-card.enabled",
            ).length;
            const badge = cat.querySelector(".ai-config-category-count");
            if (badge) badge.textContent = `${on}/${total} enabled`;
          }
          this.debouncedSaveMcp(container);
        });
      });
  }

  /* ── Save ─────────────────────────────────────── */

  private saveSkillPrefs(container: HTMLElement): void {
    const prefs: Record<string, boolean> = {};
    container.querySelectorAll<HTMLElement>("[data-skill]").forEach((card) => {
      const name = card.getAttribute("data-skill");
      const cb = card.querySelector<HTMLInputElement>('input[type="checkbox"]');
      if (name && cb) prefs[name] = cb.checked;
    });
    try {
      localStorage.setItem("stx-shell-skill-prefs", JSON.stringify(prefs));
    } catch {}
  }

  private debouncedSaveMcp(container: HTMLElement): void {
    if (this.saveTimer) clearTimeout(this.saveTimer);
    this.saveTimer = setTimeout(async () => {
      if (!this.adapter.saveMcpPrefs) return;
      const prefs: Record<string, boolean> = {};
      container
        .querySelectorAll<HTMLElement>("[data-group]")
        .forEach((card) => {
          const name = card.getAttribute("data-group");
          const cb = card.querySelector<HTMLInputElement>(
            'input[type="checkbox"]',
          );
          if (name && cb) prefs[name] = cb.checked;
        });
      try {
        await this.adapter.saveMcpPrefs(prefs);
        this.showToast();
      } catch {
        console.error("[ConfigMode] Failed to save MCP preferences");
      }
    }, 500);
  }

  private showToast(): void {
    const toast = document.getElementById("ai-config-toast");
    if (!toast) return;
    toast.classList.add("visible");
    setTimeout(() => toast.classList.remove("visible"), 1500);
  }
}
