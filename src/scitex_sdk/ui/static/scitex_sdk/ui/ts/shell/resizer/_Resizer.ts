/**
 * Resizer — draggable divider between two panels.
 *
 * Supports horizontal (left/right) and vertical (top/bottom) layouts,
 * collapse/expand toggle, localStorage persistence, and smart snap.
 *
 * Usage:
 *   import { Resizer } from 'scitex_sdk/ui/ts/shell/resizer';
 *   const resizer = new Resizer({
 *     container: '#divider',
 *     direction: 'horizontal',
 *     firstPanel: '#sidebar',
 *     secondPanel: '#main',
 *   });
 */

import { BaseComponent } from "../../_base/BaseComponent";
import type { ResizerConfig } from "./types";

const CLS = "stx-shell-resizer";
const SNAP_RADIUS = 32;
const SNAP_LOCK = 8;
const COLLAPSED_SIZE = 0;

export class Resizer extends BaseComponent<ResizerConfig> {
  private firstEl: HTMLElement;
  private secondEl: HTMLElement;
  private collapsed = false;
  private expandSize = 250;
  private toggleBtn: HTMLButtonElement | null = null;

  constructor(config: ResizerConfig) {
    super(config);

    this.firstEl = this.resolve(config.firstPanel);
    this.secondEl = this.resolve(config.secondPanel);

    this.container.classList.add(CLS);
    this.container.classList.add(
      config.direction === "vertical"
        ? `${CLS}--vertical`
        : `${CLS}--horizontal`,
    );

    if (config.showToggle !== false) {
      this.toggleBtn = this.createToggle();
      this.container.appendChild(this.toggleBtn);
    }

    this.restoreState();
    this.bindDrag();
  }

  /** Collapse the target panel. */
  collapse(): void {
    if (this.collapsed) return;
    const target = this.getTarget();
    this.expandSize = this.getSize(target);
    this.setSize(target, COLLAPSED_SIZE);
    this.collapsed = true;
    this.syncToggleIcon();
    this.saveState();
    this.config.onToggle?.(true);
  }

  /** Expand the target panel. */
  expand(): void {
    if (!this.collapsed) return;
    const target = this.getTarget();
    this.setSize(target, this.expandSize || 250);
    this.collapsed = false;
    this.syncToggleIcon();
    this.saveState();
    this.config.onToggle?.(false);
  }

  /** Toggle collapsed state. */
  toggle(): void {
    this.collapsed ? this.expand() : this.collapse();
  }

  /** Check if collapsed. */
  isCollapsed(): boolean {
    return this.collapsed;
  }

  override destroy(): void {
    this.container.classList.remove(CLS);
    if (this.toggleBtn) this.toggleBtn.remove();
    super.destroy();
  }

  // ── Private ────────────────────────────────────────────────────────

  private resolve(ref: string | HTMLElement): HTMLElement {
    if (typeof ref === "string") {
      const el = document.querySelector<HTMLElement>(ref);
      if (!el) throw new Error(`Resizer: panel not found: ${ref}`);
      return el;
    }
    return ref;
  }

  private getTarget(): HTMLElement {
    return this.config.collapseTarget === "second"
      ? this.secondEl
      : this.firstEl;
  }

  private isHorizontal(): boolean {
    return this.config.direction !== "vertical";
  }

  private getSize(el: HTMLElement): number {
    return this.isHorizontal() ? el.offsetWidth : el.offsetHeight;
  }

  private setSize(el: HTMLElement, px: number): void {
    const prop = this.isHorizontal() ? "width" : "height";
    el.style.flexBasis = `${px}px`;
    el.style[prop] = `${px}px`;
  }

  private createToggle(): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.className = `${CLS}__toggle`;
    btn.title = "Toggle panel";
    btn.type = "button";
    const icon = document.createElement("i");
    icon.className = this.getToggleIconClass(false);
    btn.appendChild(icon);
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.toggle();
    });
    return btn;
  }

  private getToggleIconClass(collapsed: boolean): string {
    if (this.isHorizontal()) {
      const collapseFirst = this.config.collapseTarget !== "second";
      if (collapseFirst)
        return collapsed ? "fas fa-chevron-right" : "fas fa-chevron-left";
      return collapsed ? "fas fa-chevron-left" : "fas fa-chevron-right";
    }
    const collapseFirst = this.config.collapseTarget !== "second";
    if (collapseFirst)
      return collapsed ? "fas fa-chevron-down" : "fas fa-chevron-up";
    return collapsed ? "fas fa-chevron-up" : "fas fa-chevron-down";
  }

  private syncToggleIcon(): void {
    if (!this.toggleBtn) return;
    const icon = this.toggleBtn.querySelector("i");
    if (icon) icon.className = this.getToggleIconClass(this.collapsed);
  }

  private bindDrag(): void {
    let startPos = 0;
    let startFirst = 0;
    let startSecond = 0;

    const onMouseDown = (e: MouseEvent) => {
      e.preventDefault();
      startPos = this.isHorizontal() ? e.clientX : e.clientY;
      startFirst = this.getSize(this.firstEl);
      startSecond = this.getSize(this.secondEl);
      document.body.style.cursor = this.isHorizontal()
        ? "col-resize"
        : "row-resize";
      document.body.style.userSelect = "none";
      this.container.classList.add(`${CLS}--active`);
      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
    };

    const onMouseMove = (e: MouseEvent) => {
      const pos = this.isHorizontal() ? e.clientX : e.clientY;
      let delta = pos - startPos;

      const minFirst = this.config.minFirst ?? 48;
      const minSecond = this.config.minSecond ?? 48;

      let newFirst = startFirst + delta;
      let newSecond = startSecond - delta;

      // Clamp
      if (newFirst < minFirst) {
        newFirst = minFirst;
        newSecond = startFirst + startSecond - minFirst;
      }
      if (newSecond < minSecond) {
        newSecond = minSecond;
        newFirst = startFirst + startSecond - minSecond;
      }

      // Snap
      const total = startFirst + startSecond;
      newFirst = this.snap(newFirst, total);
      newSecond = total - newFirst;

      this.setSize(this.firstEl, newFirst);
      this.setSize(this.secondEl, newSecond);

      // Auto-collapse detection
      if (
        newFirst <= minFirst &&
        !this.collapsed &&
        this.config.collapseTarget !== "second"
      ) {
        this.collapsed = true;
        this.syncToggleIcon();
      } else if (
        newSecond <= minSecond &&
        !this.collapsed &&
        this.config.collapseTarget === "second"
      ) {
        this.collapsed = true;
        this.syncToggleIcon();
      } else if (this.collapsed) {
        this.collapsed = false;
        this.syncToggleIcon();
      }

      this.config.onResize?.(newFirst, newSecond);
    };

    const onMouseUp = () => {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      this.container.classList.remove(`${CLS}--active`);
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      this.saveState();
    };

    this.container.addEventListener("mousedown", onMouseDown);
  }

  private snap(value: number, total: number): number {
    const percents = [0.2, 0.25, 0.33, 0.5, 0.67, 0.75, 0.8];
    for (const p of percents) {
      const snapPx = total * p;
      const dist = Math.abs(value - snapPx);
      if (dist < SNAP_LOCK) return snapPx;
      if (dist < SNAP_RADIUS) {
        const t = (SNAP_RADIUS - dist) / SNAP_RADIUS;
        return value + (snapPx - value) * t * t;
      }
    }
    return value;
  }

  private saveState(): void {
    const key = this.config.storageKey;
    if (!key) return;
    try {
      localStorage.setItem(
        key,
        JSON.stringify({
          first: this.getSize(this.firstEl),
          collapsed: this.collapsed,
          expandSize: this.expandSize,
        }),
      );
    } catch {
      /* noop */
    }
  }

  private restoreState(): void {
    const key = this.config.storageKey;
    if (!key) return;
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return;
      const state = JSON.parse(raw);
      if (state.collapsed) {
        this.expandSize = state.expandSize || 250;
        this.setSize(this.getTarget(), COLLAPSED_SIZE);
        this.collapsed = true;
        this.syncToggleIcon();
      } else if (typeof state.first === "number" && state.first > 0) {
        this.setSize(this.firstEl, state.first);
        this.expandSize = state.first;
      }
    } catch {
      /* noop */
    }
  }
}
