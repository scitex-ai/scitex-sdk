/**
 * SketchCanvas — freehand drawing tool for AI chat.
 *
 * Ported from scitex-cloud's sketch-canvas.ts.
 * Opens as modal overlay, pen/eraser/color/width, exports PNG.
 * Pure HTML5 Canvas + Pointer Events (no dependencies).
 */

import type { ImageInputManager } from "./_image-input";

function getSketchColors(): string[] {
  const isDark =
    document.documentElement.getAttribute("data-theme") !== "light";
  return isDark
    ? [
        "#ffffff",
        "#ef4444",
        "#f59e0b",
        "#22c55e",
        "#3b82f6",
        "#8b5cf6",
        "#ec4899",
        "#6b7280",
      ]
    : [
        "#1a1a2e",
        "#dc2626",
        "#d97706",
        "#16a34a",
        "#2563eb",
        "#7c3aed",
        "#db2777",
        "#4b5563",
      ];
}

const WIDTHS = [2, 5, 10];
const WIDTH_LABELS = ["Thin", "Med", "Thick"];
type Tool = "pen" | "eraser";

export class SketchCanvas {
  private overlay: HTMLElement | null = null;
  private canvas: HTMLCanvasElement | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private imageInput: ImageInputManager;
  private tool: Tool = "pen";
  private color = "#ffffff";
  private lineWidth = WIDTHS[1];
  private drawing = false;

  constructor(imageInput: ImageInputManager) {
    this.imageInput = imageInput;
  }

  open(): void {
    if (this.overlay) return;
    this.overlay = this.buildUI();
    document.body.appendChild(this.overlay);
  }

  close(): void {
    this.overlay?.remove();
    this.overlay = null;
    this.canvas = null;
    this.ctx = null;
  }

  private buildUI(): HTMLElement {
    const overlay = document.createElement("div");
    overlay.className = "stx-shell-sketch-overlay";
    overlay.style.cssText =
      "position:fixed;inset:0;background:rgba(0,0,0,0.8);z-index:10000;display:flex;align-items:center;justify-content:center;";

    const panel = document.createElement("div");
    panel.className = "stx-shell-sketch-panel";
    panel.style.cssText =
      "display:flex;flex-direction:column;gap:8px;padding:12px;background:var(--bg-secondary,#161b22);border-radius:8px;max-width:90vw;max-height:90vh;";
    overlay.appendChild(panel);

    // Toolbar
    const toolbar = document.createElement("div");
    toolbar.style.cssText =
      "display:flex;align-items:center;gap:6px;flex-wrap:wrap;";
    panel.appendChild(toolbar);

    const penBtn = this.toolBtn("Pen", "fas fa-pen", () => this.setTool("pen"));
    const eraserBtn = this.toolBtn("Eraser", "fas fa-eraser", () =>
      this.setTool("eraser"),
    );
    penBtn.classList.add("active");
    toolbar.append(penBtn, eraserBtn, this.sep());

    // Color swatches
    const colors = getSketchColors();
    this.color = colors[0];
    for (const c of colors) {
      const swatch = document.createElement("button");
      swatch.style.cssText = `width:20px;height:20px;border-radius:50%;border:2px solid transparent;background:${c};cursor:pointer;padding:0;`;
      if (c === this.color)
        swatch.style.borderColor = "var(--color-accent-fg,#58a6ff)";
      swatch.addEventListener("click", () => {
        toolbar.querySelectorAll<HTMLElement>("[data-swatch]").forEach((s) => {
          s.style.borderColor = "transparent";
        });
        swatch.style.borderColor = "var(--color-accent-fg,#58a6ff)";
        this.color = c;
        this.setTool("pen");
        toolbar.querySelectorAll<HTMLElement>("[data-tool]").forEach((b) => {
          b.style.background =
            b.dataset.tool === "pen" ? "var(--bg-tertiary,#30363d)" : "none";
        });
      });
      swatch.setAttribute("data-swatch", c);
      toolbar.appendChild(swatch);
    }

    toolbar.appendChild(this.sep());

    // Width buttons
    for (let i = 0; i < WIDTHS.length; i++) {
      const btn = document.createElement("button");
      btn.textContent = WIDTH_LABELS[i];
      btn.style.cssText =
        "padding:2px 8px;border-radius:4px;border:1px solid var(--border-default,#30363d);background:none;color:var(--fg-default,#c9d1d9);cursor:pointer;font-size:11px;";
      if (WIDTHS[i] === this.lineWidth)
        btn.style.background = "var(--bg-tertiary,#30363d)";
      btn.addEventListener("click", () => {
        toolbar.querySelectorAll<HTMLElement>("[data-width]").forEach((b) => {
          b.style.background = "none";
        });
        btn.style.background = "var(--bg-tertiary,#30363d)";
        this.lineWidth = WIDTHS[i];
      });
      btn.setAttribute("data-width", String(WIDTHS[i]));
      toolbar.appendChild(btn);
    }

    // Canvas
    this.canvas = document.createElement("canvas");
    this.canvas.width = 1200;
    this.canvas.height = 800;
    this.canvas.style.cssText =
      "width:100%;max-height:70vh;border-radius:4px;cursor:crosshair;touch-action:none;";
    panel.appendChild(this.canvas);
    this.ctx = this.canvas.getContext("2d")!;
    this.ctx.fillStyle = this.canvasBg();
    this.ctx.fillRect(0, 0, 1200, 800);
    this.bindDrawing(this.canvas);

    // Action buttons
    const actions = document.createElement("div");
    actions.style.cssText = "display:flex;gap:8px;justify-content:flex-end;";

    const clearBtn = this.actionBtn("Clear", false, () => this.clearCanvas());
    const cancelBtn = this.actionBtn("Cancel", false, () => this.close());
    const doneBtn = this.actionBtn("Done", true, () => this.done());
    actions.append(clearBtn, cancelBtn, doneBtn);
    panel.appendChild(actions);

    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) this.close();
    });

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        this.close();
        document.removeEventListener("keydown", onKey);
      }
    };
    document.addEventListener("keydown", onKey);

    return overlay;
  }

  private toolBtn(
    label: string,
    icon: string,
    onClick: () => void,
  ): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.innerHTML = `<i class="${icon}"></i> ${label}`;
    btn.style.cssText =
      "padding:4px 10px;border-radius:4px;border:1px solid var(--border-default,#30363d);background:none;color:var(--fg-default,#c9d1d9);cursor:pointer;font-size:12px;";
    btn.setAttribute("data-tool", label.toLowerCase());
    btn.addEventListener("click", () => {
      const toolbar = btn.parentElement!;
      toolbar.querySelectorAll<HTMLElement>("[data-tool]").forEach((b) => {
        b.style.background = "none";
      });
      btn.style.background = "var(--bg-tertiary,#30363d)";
      onClick();
    });
    return btn;
  }

  private actionBtn(
    label: string,
    primary: boolean,
    onClick: () => void,
  ): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.textContent = label;
    btn.style.cssText = primary
      ? "padding:6px 16px;border-radius:4px;border:none;background:var(--color-accent-fg,#58a6ff);color:#fff;cursor:pointer;"
      : "padding:6px 16px;border-radius:4px;border:1px solid var(--border-default,#30363d);background:none;color:var(--fg-default,#c9d1d9);cursor:pointer;";
    btn.addEventListener("click", onClick);
    return btn;
  }

  private sep(): HTMLElement {
    const el = document.createElement("span");
    el.style.cssText =
      "width:1px;height:20px;background:var(--border-default,#30363d);margin:0 4px;";
    return el;
  }

  private bindDrawing(canvas: HTMLCanvasElement): void {
    canvas.addEventListener("pointerdown", (e) => this.startDraw(e));
    canvas.addEventListener("pointermove", (e) => this.draw(e));
    canvas.addEventListener("pointerup", () => (this.drawing = false));
    canvas.addEventListener("pointerleave", () => (this.drawing = false));
  }

  private startDraw(e: PointerEvent): void {
    this.drawing = true;
    const ctx = this.ctx!;
    ctx.beginPath();
    const { x, y } = this.coords(e);
    ctx.moveTo(x, y);
  }

  private draw(e: PointerEvent): void {
    if (!this.drawing || !this.ctx) return;
    const ctx = this.ctx;
    const { x, y } = this.coords(e);
    ctx.lineWidth = this.lineWidth;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    if (this.tool === "eraser") {
      ctx.globalCompositeOperation = "destination-out";
      ctx.strokeStyle = "rgba(0,0,0,1)";
    } else {
      ctx.globalCompositeOperation = "source-over";
      ctx.strokeStyle = this.color;
    }
    ctx.lineTo(x, y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x, y);
  }

  private coords(e: PointerEvent): { x: number; y: number } {
    const rect = this.canvas!.getBoundingClientRect();
    return {
      x: ((e.clientX - rect.left) / rect.width) * this.canvas!.width,
      y: ((e.clientY - rect.top) / rect.height) * this.canvas!.height,
    };
  }

  private setTool(t: Tool): void {
    this.tool = t;
  }

  private canvasBg(): string {
    const isDark =
      document.documentElement.getAttribute("data-theme") !== "light";
    return isDark ? "#1a1a2e" : "#ffffff";
  }

  private clearCanvas(): void {
    if (!this.ctx || !this.canvas) return;
    this.ctx.globalCompositeOperation = "source-over";
    this.ctx.fillStyle = this.canvasBg();
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
  }

  private done(): void {
    if (!this.canvas) return;
    const dataUrl = this.canvas.toDataURL("image/png");
    this.imageInput.addImageFromDataUrl(dataUrl, "image/png");
    this.close();
  }
}
