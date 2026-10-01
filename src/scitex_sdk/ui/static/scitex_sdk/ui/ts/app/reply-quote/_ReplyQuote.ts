/**
 * ReplyQuote — a truncated quote of the message being replied to.
 *
 * Built base-first at scitex-cards' request (the operator's item 15), before
 * they wrote a private one. Their constraint drove the whole design: it sits
 * INSIDE a bubble already colour-coded by sender, so it must not choose its
 * own colours — the stylesheet derives everything from `currentColor`.
 *
 * The behaviour worth stating: a quote whose original cannot be found renders
 * ORPHANED rather than staying clickable and silently doing nothing. A dead
 * link that looks alive is the same failure as a receipt that cannot say
 * "unknown" — it reports success it has not verified.
 */

import type { ReplyQuoteConfig } from "./types";

const FLASH_MS_DEFAULT = 1200;
const FLASH_CLASS = "stx-app-reply-quote-target--flash";

export class ReplyQuote {
  readonly el: HTMLButtonElement;
  private readonly config: ReplyQuoteConfig;

  constructor(config: ReplyQuoteConfig) {
    this.config = config;
    this.el = document.createElement("button");
    this.el.type = "button";
    this.el.className = "stx-app-reply-quote";

    const author = document.createElement("span");
    author.className = "stx-app-reply-quote__author";
    author.textContent = config.author;

    const text = document.createElement("span");
    text.className = "stx-app-reply-quote__text";
    text.textContent = config.text;

    this.el.append(author, text);
    this.el.setAttribute(
      "aria-label",
      `Reply to ${config.author}: ${config.text}`,
    );
    this.el.addEventListener("click", () => this.activate());

    // Orphaned at construction when there is no way to reach an original:
    // no custom handler AND no target id that currently resolves.
    if (!config.onActivate && !this.resolveTarget()) this.markOrphaned();
  }

  /** Jump to the original. Returns false when it could not be reached. */
  activate(): boolean {
    if (this.config.onActivate) {
      const handled = this.config.onActivate(this.config.targetId);
      if (!handled) this.markOrphaned();
      return handled;
    }

    const target = this.resolveTarget();
    if (!target) {
      this.markOrphaned();
      return false;
    }

    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.classList.add(FLASH_CLASS);
    window.setTimeout(
      () => target.classList.remove(FLASH_CLASS),
      this.config.flashMs ?? FLASH_MS_DEFAULT,
    );
    return true;
  }

  /** Whether this quote currently believes it can reach its original. */
  get orphaned(): boolean {
    return this.el.classList.contains("stx-app-reply-quote--orphaned");
  }

  private resolveTarget(): HTMLElement | null {
    const id = this.config.targetId;
    if (!id) return null;
    return document.getElementById(id);
  }

  private markOrphaned(): void {
    this.el.classList.add("stx-app-reply-quote--orphaned");
    this.el.disabled = true;
    this.el.title = "The original message is no longer available";
  }
}

/** Convenience: build a reply quote in one call. */
export function renderReplyQuote(config: ReplyQuoteConfig): ReplyQuote {
  return new ReplyQuote(config);
}
