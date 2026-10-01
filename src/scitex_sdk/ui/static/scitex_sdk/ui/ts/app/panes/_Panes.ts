/**
 * Mobile panes: a multi-column app becomes one column per screen on phones.
 *
 *   <div data-stx-panes="figrecipe" style="--stx-panes-columns: 280px 1fr 320px">
 *     <section data-stx-pane="data" data-stx-label="Data" data-stx-icon="📊">…</section>
 *     <section data-stx-pane="plot" data-stx-label="Plot" data-stx-icon="📈">…</section>
 *   </div>
 *
 * Above the phone breakpoint nothing changes: the panes sit side by side.
 * At or below it the root gets `stx-panes--single`, a sticky tab bar sits above
 * the panes and only the active pane shows. The active pane changes by explicit
 * tab tap/click, accessible keyboard activation (arrow keys on the tablist), or
 * a named command (`show()`).
 *
 * Horizontal swipe-to-switch-tab is DISABLED by default (operator mobile
 * ruling 7724-7725): it conflicts with pan/zoom/scroll inside Writer PDF,
 * FigRecipe canvas, graphs, editors and tables. Apps whose content has no
 * horizontal gestures may opt in with `swipeToSwitch: true`; when opted in,
 * swipes beginning inside a horizontal scroller, a text input, or interactive
 * content (canvas, svg, table, iframe, PDF/canvas/graph/editor wrappers) are
 * ignored.
 *
 * The active pane is remembered per app in sessionStorage.
 */

import { gettext } from "../../_base/gettext";
import type {
  PaneInfo,
  PanesChangeDetail,
  PanesMedia,
  PanesOptions,
  PanesStorage,
} from "./types";

export const PANES_ATTRIBUTE = "data-stx-panes";
export const PANE_ATTRIBUTE = "data-stx-pane";
export const ACTIVE_ATTRIBUTE = "data-stx-pane-active";
export const SINGLE_CLASS = "stx-panes--single";
export const PANES_CHANGE = "stx-panes:change";
export const PHONE_QUERY = "(max-width: 640px)";
export const STORAGE_PREFIX = "stx-panes:";

const CLS = "stx-panes";
const SWIPE_MIN_PX = 60;
const SWIPE_AXIS_RATIO = 1.5;
const NO_SWIPE_SELECTOR =
  "input, textarea, select, [contenteditable=''], [contenteditable='true'], [data-stx-no-swipe], " +
  "canvas, svg, table, iframe, embed, object, " +
  "[role='img'], [role='application'], [data-stx-interactive], " +
  ".stx-pdf-viewer, .stx-canvas, .stx-graph, .stx-editor";

function defaultMedia(): PanesMedia | null {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return null;
  return window.matchMedia(PHONE_QUERY);
}

function defaultStorage(): PanesStorage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function slug(value: string): string {
  return value.replace(/[^A-Za-z0-9_-]+/g, "-");
}

/** True when a gesture starting at `target` belongs to something inside the pane. */
export function startsInsideOwnGesture(target: Element | null, root: Element): boolean {
  for (let el: Element | null = target; el && el !== root; el = el.parentElement) {
    if (el.matches(NO_SWIPE_SELECTOR)) return true;
    if (el.scrollWidth > el.clientWidth + 1) {
      const overflow = getComputedStyle(el).overflowX;
      if (overflow === "auto" || overflow === "scroll") return true;
    }
  }
  return false;
}

export class Panes {
  readonly root: HTMLElement;
  readonly app: string;
  readonly panes: PaneInfo[];
  readonly tablist: HTMLElement;
  private readonly tabs = new Map<string, HTMLButtonElement>();
  private readonly storage: PanesStorage | null;
  private activeId: string;
  private touchStart: { x: number; y: number } | null = null;

  constructor(root: HTMLElement, options: PanesOptions = {}) {
    this.root = root;
    this.app =
      options.app ||
      root.getAttribute(PANES_ATTRIBUTE) ||
      (typeof location !== "undefined" ? location.pathname : "default");
    this.storage = options.storage === undefined ? defaultStorage() : options.storage;
    this.panes = this.collectPanes();
    root.classList.add(CLS);

    this.tablist = this.renderTabs();
    root.insertBefore(this.tablist, root.firstChild);

    this.activeId = this.initialPane();
    this.apply(this.activeId);

    const media = options.media === undefined ? defaultMedia() : options.media;
    this.setSingle(Boolean(media?.matches));
    media?.addEventListener("change", (event) => this.setSingle(event.matches));

    // Horizontal swipe-to-switch-tab: DISABLED by default (operator mobile
    // ruling 7724-7725). Content gestures (PDF pan, canvas zoom, table
    // scroll) must not accidentally change the active tab. Apps that have
    // no horizontal content gestures can opt in with `swipeToSwitch: true`.
    if (options.swipeToSwitch) {
      root.addEventListener("touchstart", (event) => this.onTouchStart(event), { passive: true });
      root.addEventListener("touchend", (event) => this.onTouchEnd(event), { passive: true });
    }
  }

  get active(): string {
    return this.activeId;
  }

  get single(): boolean {
    return this.root.classList.contains(SINGLE_CLASS);
  }

  /** Make `id` the active pane. Returns false for an unknown id. */
  show(id: string): boolean {
    if (!this.panes.some((pane) => pane.id === id)) return false;
    const previous = this.activeId;
    this.apply(id);
    try {
      this.storage?.setItem(STORAGE_PREFIX + this.app, id);
    } catch {
      // Private mode or a full quota: the pane still switches, it just is not remembered.
    }
    if (previous !== id) {
      const detail: PanesChangeDetail = { app: this.app, pane: id, previous };
      this.root.dispatchEvent(new CustomEvent(PANES_CHANGE, { detail, bubbles: true }));
    }
    return true;
  }

  /** Move by `step` panes in tab order, clamped at the ends. */
  step(step: number): boolean {
    const index = this.panes.findIndex((pane) => pane.id === this.activeId);
    const next = this.panes[index + step];
    return next ? this.show(next.id) : false;
  }

  private collectPanes(): PaneInfo[] {
    const elements = Array.from(this.root.children).filter(
      (child): child is HTMLElement => child instanceof HTMLElement && child.hasAttribute(PANE_ATTRIBUTE),
    );
    return elements
      .map((element, index) => {
        const id = element.getAttribute(PANE_ATTRIBUTE) || String(index);
        const declared = element.getAttribute("data-stx-order");
        const order = declared === null || declared === "" ? NaN : Number(declared);
        if (Number.isFinite(order)) element.style.order = String(order);
        return {
          id,
          label: element.getAttribute("data-stx-label") || id,
          icon: element.getAttribute("data-stx-icon") || "",
          order: Number.isFinite(order) ? order : index,
          element,
          index,
        };
      })
      .sort((a, b) => a.order - b.order || a.index - b.index)
      .map(({ id, label, icon, order, element }) => ({ id, label, icon, order, element }));
  }

  private renderTabs(): HTMLElement {
    const tablist = document.createElement("div");
    tablist.className = `${CLS}__tabs`;
    tablist.setAttribute("role", "tablist");
    tablist.setAttribute("aria-label", gettext("Sections"));

    for (const pane of this.panes) {
      const paneDomId = pane.element.id || `${CLS}-${slug(this.app)}-${slug(pane.id)}`;
      pane.element.id = paneDomId;
      pane.element.classList.add(`${CLS}__pane`);

      const tab = document.createElement("button");
      tab.type = "button";
      tab.className = `${CLS}__tab`;
      tab.id = `${paneDomId}-tab`;
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-controls", paneDomId);
      tab.dataset.stxPaneTab = pane.id;
      if (pane.icon) {
        const icon = document.createElement("span");
        icon.className = `${CLS}__tab-icon`;
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = pane.icon;
        tab.appendChild(icon);
      }
      const label = document.createElement("span");
      label.className = `${CLS}__tab-label`;
      label.textContent = pane.label;
      tab.appendChild(label);
      tab.addEventListener("click", () => this.show(pane.id));
      pane.element.setAttribute("aria-labelledby", tab.id);

      this.tabs.set(pane.id, tab);
      tablist.appendChild(tab);
    }

    tablist.addEventListener("keydown", (event) => {
      const delta = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
      if (!delta || !this.step(delta)) return;
      event.preventDefault();
      this.tabs.get(this.activeId)?.focus();
    });
    return tablist;
  }

  private initialPane(): string {
    const known = (id: string | null | undefined): id is string =>
      Boolean(id) && this.panes.some((pane) => pane.id === id);
    let stored: string | null = null;
    try {
      stored = this.storage?.getItem(STORAGE_PREFIX + this.app) ?? null;
    } catch {
      stored = null;
    }
    if (known(stored)) return stored;
    const declared = this.root.getAttribute("data-stx-active");
    if (known(declared)) return declared;
    return this.panes[0]?.id ?? "";
  }

  private apply(id: string): void {
    this.activeId = id;
    for (const pane of this.panes) {
      const isActive = pane.id === id;
      pane.element.toggleAttribute(ACTIVE_ATTRIBUTE, isActive);
      const tab = this.tabs.get(pane.id);
      tab?.setAttribute("aria-selected", String(isActive));
      tab?.setAttribute("tabindex", isActive ? "0" : "-1");
    }
    const tab = this.tabs.get(id);
    if (this.single && tab && typeof tab.scrollIntoView === "function") {
      tab.scrollIntoView({ block: "nearest", inline: "nearest" });
    }
  }

  private setSingle(single: boolean): void {
    this.root.classList.toggle(SINGLE_CLASS, single);
    for (const pane of this.panes) {
      if (single) pane.element.setAttribute("role", "tabpanel");
      else pane.element.removeAttribute("role");
    }
  }

  private onTouchStart(event: TouchEvent): void {
    this.touchStart = null;
    if (!this.single || event.touches.length !== 1) return;
    if (startsInsideOwnGesture(event.target as Element | null, this.root)) return;
    this.touchStart = { x: event.touches[0].clientX, y: event.touches[0].clientY };
  }

  private onTouchEnd(event: TouchEvent): void {
    const start = this.touchStart;
    this.touchStart = null;
    const touch = event.changedTouches[0];
    if (!start || !touch) return;
    const dx = touch.clientX - start.x;
    const dy = touch.clientY - start.y;
    if (Math.abs(dx) < SWIPE_MIN_PX || Math.abs(dx) < Math.abs(dy) * SWIPE_AXIS_RATIO) return;
    this.step(dx < 0 ? 1 : -1);
  }
}
