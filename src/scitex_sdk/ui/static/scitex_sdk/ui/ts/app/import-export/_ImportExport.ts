/**
 * ImportExport — the standard import/export pattern (compass L623).
 *
 * A trigger opens a panel of format options; picking one shows a confirm
 * bar (the format list is long enough that an accidental tap on "Zotero"
 * should not immediately fire a transfer); confirming emits
 * `stx-import-export:confirm` and the APP performs the transfer — the
 * component owns the pattern, not the data or the bytes.
 *
 * Usage:
 *   import { ImportExport, IMPORT_EXPORT_CONFIRM } from
 *     "scitex_sdk/ui/ts/app/import-export";
 *
 *   const ie = new ImportExport({
 *     container: "#export-menu",
 *     direction: "export",
 *     formats: [
 *       { id: "bibtex", label: "BibTeX" },
 *       { id: "ris", label: "RIS", detail: "for EndNote" },
 *       { id: "csl-json", label: "CSL JSON" },
 *       { id: "pdf", label: "PDF" },
 *     ],
 *   });
 *   ie.container.addEventListener(IMPORT_EXPORT_CONFIRM, (e) => {
 *     const { direction, formatId, formatLabel } =
 *       (e as CustomEvent<ImportExportDetail>).detail;
 *     // perform the actual export in formatId
 *   });
 *
 * Confirm/cancel bar buttons use the standard .stx-button (form-controls).
 */

import { BaseComponent } from "../../_base/BaseComponent";
import type {
  FormatOption,
  ImportExportConfig,
  ImportExportDetail,
} from "./types";

const CLS = "stx-app-import-export";

/** Event emitted on the container when the user confirms a format. */
export const IMPORT_EXPORT_CONFIRM = "stx-import-export:confirm";

type View = "list" | "confirm";

export class ImportExport extends BaseComponent<ImportExportConfig> {
  private trigger: HTMLButtonElement;
  private panel: HTMLElement;
  private body: HTMLElement;
  private selected: FormatOption | null = null;
  private view: View = "list";
  private open = false;
  private outsideClickHandler: (e: MouseEvent) => void;
  private keyHandler: (e: KeyboardEvent) => void;

  constructor(config: ImportExportConfig) {
    super(config);

    this.container.className = CLS;

    this.trigger = document.createElement("button");
    this.trigger.type = "button";
    this.trigger.className = `${CLS}__trigger stx-button`;
    this.trigger.textContent = config.title ?? (config.direction === "export" ? "Export" : "Import");
    this.trigger.setAttribute("aria-haspopup", "true");

    this.panel = document.createElement("div");
    this.panel.className = `${CLS}__panel`;

    this.body = document.createElement("div");
    this.body.className = `${CLS}__body`;
    this.panel.appendChild(this.body);

    this.container.appendChild(this.trigger);
    this.container.appendChild(this.panel);

    this.trigger.addEventListener("click", () => this.toggle());

    this.outsideClickHandler = (e: MouseEvent): void => {
      if (!this.container.contains(e.target as Node)) {
        this.close();
      }
    };
    this.keyHandler = (e: KeyboardEvent): void => {
      if (e.key !== "Escape") {
        return;
      }
      // Esc steps BACK out of the confirm bar rather than closing outright —
      // the user was one tap from committing to a format, not from the menu.
      if (this.view === "confirm") {
        this.showList();
      } else {
        this.close();
      }
    };
    document.addEventListener("click", this.outsideClickHandler);
    document.addEventListener("keydown", this.keyHandler);
  }

  private title(): string {
    return this.config.title ?? (this.config.direction === "export" ? "Export" : "Import");
  }

  private confirmText(label: string): string {
    if (this.config.confirmText) {
      return this.config.confirmText(label);
    }
    return this.config.direction === "export"
      ? `Export as ${label}?`
      : `Import ${label}?`;
  }

  toggle(): void {
    if (this.open) {
      this.close();
    } else {
      this.open = true;
      this.view = "list";
      this.render();
      this.container.classList.add(`${CLS}--open`);
      this.trigger.setAttribute("aria-expanded", "true");
    }
  }

  close(): void {
    if (!this.open) {
      return;
    }
    this.open = false;
    this.container.classList.remove(`${CLS}--open`);
    this.trigger.setAttribute("aria-expanded", "false");
  }

  /** Render the current view (list or confirm bar) into the panel body. */
  private render(): void {
    if (this.view === "confirm") {
      this.renderConfirm();
    } else {
      this.renderList();
    }
  }

  private renderList(): void {
    this.body.innerHTML = "";

    const title = document.createElement("div");
    title.className = `${CLS}__title`;
    title.textContent = this.title();
    this.body.appendChild(title);

    if (this.config.formats.length === 0) {
      const empty = document.createElement("div");
      empty.className = `${CLS}__empty`;
      empty.textContent = "No formats available";
      this.body.appendChild(empty);
      return;
    }

    const list = document.createElement("div");
    list.className = `${CLS}__list`;
    for (const format of this.config.formats) {
      const option = document.createElement("button");
      option.type = "button";
      option.className = `${CLS}__format`;
      option.setAttribute("role", "option");

      const label = document.createElement("span");
      label.className = `${CLS}__format-label`;
      label.textContent = format.label;
      option.appendChild(label);

      if (format.detail) {
        const detail = document.createElement("span");
        detail.className = `${CLS}__format-detail`;
        detail.textContent = format.detail;
        option.appendChild(detail);
      }

      option.addEventListener("click", () => this.select(format));
      list.appendChild(option);
    }
    this.body.appendChild(list);
  }

  private renderConfirm(): void {
    const format = this.selected;
    if (!format) {
      this.showList();
      return;
    }
    this.body.innerHTML = "";

    const text = document.createElement("div");
    text.className = `${CLS}__confirm-text`;
    text.textContent = this.confirmText(format.label);
    this.body.appendChild(text);

    const bar = document.createElement("div");
    bar.className = `${CLS}__confirm-bar`;

    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = `${CLS}__cancel stx-button`;
    cancel.textContent = "Cancel";
    cancel.addEventListener("click", () => this.showList());
    bar.appendChild(cancel);

    const confirm = document.createElement("button");
    confirm.type = "button";
    confirm.className = `${CLS}__confirm stx-button stx-button--primary`;
    confirm.textContent = this.config.direction === "export" ? "Export" : "Import";
    confirm.addEventListener("click", () => this.confirm(format));
    bar.appendChild(confirm);

    this.body.appendChild(bar);
  }

  private select(format: FormatOption): void {
    this.selected = format;
    this.view = "confirm";
    this.render();
  }

  private showList(): void {
    this.selected = null;
    this.view = "list";
    this.render();
  }

  /** The user confirmed: emit the event and close. The app does the rest. */
  private confirm(format: FormatOption): void {
    this.close();
    this.emit(IMPORT_EXPORT_CONFIRM, {
      direction: this.config.direction,
      formatId: format.id,
      formatLabel: format.label,
    } satisfies ImportExportDetail);
  }

  override destroy(): void {
    document.removeEventListener("click", this.outsideClickHandler);
    document.removeEventListener("keydown", this.keyHandler);
    super.destroy();
  }
}
