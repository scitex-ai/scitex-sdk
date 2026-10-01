/**
 * Inline Input Helper for WorkspaceFilesTree
 * Ported from scitex-cloud (no API deps)
 */

export type InlineInputType = "file" | "directory";

export interface InlineInputOptions {
  container: HTMLElement;
  insertMode: "after-sibling" | "prepend";
  sibling?: HTMLElement;
  type: InlineInputType;
  onSubmit: (name: string) => Promise<void>;
}

export function attachInlineInput(options: InlineInputOptions): void {
  const { container, insertMode, sibling, type, onSubmit } = options;

  const inputRow = document.createElement("div");
  inputRow.className = `wft-item wft-${type} wft-inline-create`;

  const iconClass =
    type === "file"
      ? "fas fa-file wft-inline-create-icon-file"
      : "fas fa-folder wft-inline-create-icon-folder";

  const placeholder = type === "file" ? "filename.ext" : "folder name";

  inputRow.innerHTML = `
    <span class="wft-spacer"></span>
    <span class="wft-icon"><i class="${iconClass}"></i></span>
    <input type="text" class="wft-inline-input" placeholder="${placeholder}" />
  `;

  if (insertMode === "after-sibling" && sibling) {
    sibling.after(inputRow);
  } else {
    container.insertBefore(inputRow, container.firstChild);
  }

  const input = inputRow.querySelector(".wft-inline-input") as HTMLInputElement;
  if (!input) {
    inputRow.remove();
    return;
  }

  input.focus();

  let submitted = false;
  const cleanup = (): void => {
    inputRow.remove();
  };
  const submit = async (): Promise<void> => {
    if (submitted) return;
    submitted = true;
    const name = input.value.trim();
    if (!name) {
      cleanup();
      return;
    }
    await onSubmit(name);
    cleanup();
  };

  input.addEventListener("blur", () => {
    setTimeout(() => submit(), 100);
  });

  input.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      input.blur();
    } else if (e.key === "Escape") {
      e.preventDefault();
      cleanup();
    }
  });
}
