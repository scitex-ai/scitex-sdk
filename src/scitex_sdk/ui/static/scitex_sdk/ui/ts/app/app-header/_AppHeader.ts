/**
 * AppHeader — the ONE canonical app header row.
 *
 * Every project-scoped app presents the SAME header template, so a user can
 * predict it across apps:
 *
 *     [ leaf title ] [ v<version> ] [ project selector ] ...... [ actions ]
 *
 * Placement is deliberately NOT a per-app decision. The project selector lives
 * in the canonical slot (`.stx-app-header__slot--project-selector`, styled in
 * css/app/project-selector.css — the single definition the cross-app contract
 * pins) and is pushed to the right edge together with the actions by that
 * slot's own auto-margin. There is no second header template anywhere in this
 * package, and a leaf with its own header (FigRecipe shipped one) replaces it
 * with this component rather than restyling a copy.
 *
 * WHERE THE VALUES COME FROM — `readShellProps()` is the reader half of the
 * scitex-app shell contract (`<meta name="stx-app-shell">`, their PR #199).
 * Precedence is explicit-config > contract payload > mount attributes, because
 * the payload is the host's declaration and the explicit argument is the app
 * overriding it for this surface.
 *
 * THE PROJECT SLOT IS NOT ALWAYS RENDERED. scitex-app refuses to emit a project
 * provider for a user-scoped app ("the global header must never force a
 * selector"), so this reader refuses to render the slot for one. An app that
 * drives the component directly and declares no scope keeps the slot, which is
 * the shape FigRecipe and the hub use.
 *
 * Usage (contract-driven — a host that emits `stx-app-shell` needs no JS at all
 * beyond the pre-built module):
 *
 *     <meta name="stx-app-shell" content='{"app":"writer","title":"Writer",...}'>
 *
 * Usage (app-driven):
 *
 *     import { AppHeader } from "scitex_sdk/ui/ts/app/app-header";
 *     const header = new AppHeader({
 *       container: "#app-header-root",
 *       title: gettext("Writer"),      // the leaf owns translation
 *       version: "1.4.0",              // or omit -> data-app-version / payload
 *     });
 *     header.projectSlot.appendChild(myProjectSelector.element);
 *     header.addAction(settingsButton);
 */

import { BaseComponent } from "../../_base/BaseComponent";
import type { AppHeaderConfig, ShellAction, ShellProps } from "./types";
import {
  orderedActions,
  readShellProps,
  resolveAppTitle,
  resolveAppVersion,
} from "./types";

/** The de-facto registry: the class-manifest guard reads this declaration. */
const CLS = "stx-app-header";

/**
 * Emitted on the container (bubbling) when a header action that names a
 * COMMAND is activated. The detail's `command` id is the same id the app's
 * keymap registry uses, so keyboard, touch and mouse resolve ONE id.
 */
export const APP_HEADER_COMMAND = "stx-app-header:command";

export class AppHeader extends BaseComponent<AppHeaderConfig> {
  /** The `<header>` element this component owns. */
  readonly headerEl: HTMLElement;
  /** Leaf title — a span (NOT a heading): a mounted leaf must not add a second H1. */
  readonly titleEl: HTMLSpanElement;
  /** Version badge; `hidden` when the version is unknown. */
  readonly versionEl: HTMLSpanElement;
  /** Canonical project-selector slot, or `null` for a user-scoped app. */
  readonly projectSlot: HTMLDivElement | null;
  /** App-specific actions slot. */
  readonly actionsEl: HTMLDivElement;
  /** The contract payload this header rendered from, when the page carried one. */
  readonly shellProps: ShellProps | null;

  constructor(config: AppHeaderConfig) {
    super(config);

    const doc = this.container.ownerDocument ?? document;
    this.shellProps = config.shellProps ?? readShellProps(doc);

    this.headerEl = document.createElement("header");
    this.headerEl.className = CLS;

    this.titleEl = document.createElement("span");
    this.titleEl.className = `${CLS}__title`;
    this.titleEl.textContent =
      config.title ??
      (this.shellProps?.title || resolveAppTitle(this.container)) ??
      "";

    this.versionEl = document.createElement("span");
    this.versionEl.className = `${CLS}__version`;

    this.actionsEl = document.createElement("div");
    this.actionsEl.className = `${CLS}__actions`;

    this.headerEl.append(this.titleEl, this.versionEl);

    // Canonical slot, canonical class. Its CSS is owned by
    // css/app/project-selector.css and pinned by
    // tests/develop/test_project_selector_contract.py — defining it a second
    // time here is the duplicate-definition defect this repo keeps carding.
    if (config.projectSlot ?? this.wantsProjectSlot()) {
      this.projectSlot = document.createElement("div");
      this.projectSlot.className = `${CLS}__slot--project-selector`;
      this.headerEl.appendChild(this.projectSlot);
    } else {
      this.projectSlot = null;
    }

    this.headerEl.appendChild(this.actionsEl);
    this.container.appendChild(this.headerEl);

    this.setVersion(
      config.version ||
        this.shellProps?.version ||
        resolveAppVersion(this.container),
    );
    for (const element of config.actions ?? []) this.actionsEl.appendChild(element);
    for (const action of orderedActions(this.shellProps?.actions)) {
      this.actionsEl.appendChild(this.buildAction(action));
    }
  }

  /**
   * The slot exists for a project-scoped app that declares a provider. With no
   * payload at all (an app driving the component directly) it stays, because
   * that is what the header template promises.
   */
  private wantsProjectSlot(): boolean {
    if (!this.shellProps) return true;
    return this.shellProps.scope === "project" && Boolean(this.shellProps.project);
  }

  /**
   * One action control. A control that names NEITHER a command nor an href does
   * nothing and renders identically to a working one (the /apps/storage/
   * measurement), so it is refused here as well as at the writer.
   */
  private buildAction(action: ShellAction): HTMLElement {
    if (!action.command && !action.href) {
      throw new Error(
        `AppHeader: action ${JSON.stringify(action.id)} names neither a command ` +
          `nor an href. A control that does nothing must not render.`,
      );
    }

    let element: HTMLElement;
    if (action.href) {
      const anchor = document.createElement("a");
      anchor.href = action.href;
      element = anchor;
    } else {
      const button = document.createElement("button");
      button.type = "button";
      element = button;
    }
    element.className = `${CLS}__action`;
    element.textContent = action.label;
    element.setAttribute("data-stx-action", action.id);

    if (action.command) {
      const command = action.command;
      element.setAttribute("data-stx-command", command);
      element.addEventListener("click", () => {
        this.emit(APP_HEADER_COMMAND, { command, action: action.id });
      });
    }
    return element;
  }

  /** Set the leaf title (the leaf owns the translation of what it passes). */
  setTitle(title: string): void {
    this.titleEl.textContent = title;
  }

  /**
   * Set the version badge. An unknown/empty version HIDES the badge (it never
   * renders a placeholder): the element stays in place so a later
   * `setVersion()` reveals it without rebuilding the header row.
   */
  setVersion(version: string | null | undefined): void {
    const resolved = (version ?? "").trim();
    if (resolved === "") {
      this.versionEl.hidden = true;
      this.versionEl.textContent = "";
      return;
    }
    this.versionEl.hidden = false;
    this.versionEl.textContent = `${this.config.versionPrefix ?? "v"}${resolved}`;
  }

  /** Append one app-specific action into the actions slot. */
  addAction(element: HTMLElement): void {
    this.actionsEl.appendChild(element);
  }

  override destroy(): void {
    this.headerEl.remove();
    super.destroy();
  }
}
