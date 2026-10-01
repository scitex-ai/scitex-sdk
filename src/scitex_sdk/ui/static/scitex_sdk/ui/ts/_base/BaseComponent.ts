/**
 * BaseComponent — shared base for all scitex-ui components.
 *
 * Provides container resolution, lifecycle hooks, and event dispatch.
 */

import type { BaseComponentConfig } from "./types";

export abstract class BaseComponent<
  C extends BaseComponentConfig = BaseComponentConfig,
> {
  protected container: HTMLElement;
  protected config: C;

  constructor(config: C) {
    this.config = config;
    const el =
      typeof config.container === "string"
        ? document.querySelector<HTMLElement>(config.container)
        : config.container;

    if (!el) {
      throw new Error(
        `${this.constructor.name}: container not found: ${config.container}`,
      );
    }
    this.container = el;
  }

  /** Emit a custom event on the container. */
  protected emit<T>(name: string, detail: T): void {
    this.container.dispatchEvent(
      new CustomEvent(name, { detail, bubbles: true }),
    );
  }

  /** Destroy the component and clean up DOM. */
  destroy(): void {
    this.container.innerHTML = "";
  }
}
