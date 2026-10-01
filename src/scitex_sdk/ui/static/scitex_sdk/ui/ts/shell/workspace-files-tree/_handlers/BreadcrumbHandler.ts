/**
 * BreadcrumbHandler — a clickable path bar above the file tree.
 *
 * Renders the current root's absolute path as segments ("/ › home › proj › …");
 * clicking a segment re-roots the tree to that ancestor directory via the
 * supplied navigate callback. Lets the user escape the launch folder and browse
 * from the filesystem root. Opt-in (TreeConfig.showBreadcrumb).
 */

const CLS = "wft-breadcrumb";

interface Segment {
  label: string;
  path: string;
}

export class BreadcrumbHandler {
  private el: HTMLElement | null = null;

  constructor(private readonly onNavigate: (absPath: string) => void) {}

  /** Render the breadcrumb for `rootPath` as the first child of `container`. */
  render(container: HTMLElement, rootPath: string | null): void {
    if (!this.el) {
      this.el = document.createElement("nav");
      this.el.className = CLS;
      this.el.setAttribute("aria-label", "Folder path");
      container.prepend(this.el);
    }
    this.el.innerHTML = "";
    if (!rootPath) return;

    const segments = this.toSegments(rootPath);
    segments.forEach((seg, i) => {
      if (i > 0) {
        const sep = document.createElement("span");
        sep.className = `${CLS}__separator`;
        sep.textContent = "›";
        sep.setAttribute("aria-hidden", "true");
        this.el!.appendChild(sep);
      }
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `${CLS}__segment`;
      // Mark the current (last) segment so it can be de-emphasised / non-active.
      if (i === segments.length - 1) {
        btn.classList.add(`${CLS}__segment--current`);
      }
      btn.textContent = seg.label;
      btn.title = seg.path;
      btn.addEventListener("click", () => this.onNavigate(seg.path));
      this.el!.appendChild(btn);
    });
  }

  /** Split an absolute POSIX path into segments from filesystem root to leaf. */
  private toSegments(absPath: string): Segment[] {
    const parts = absPath.split("/").filter(Boolean);
    const segments: Segment[] = [{ label: "/", path: "/" }];
    let acc = "";
    for (const part of parts) {
      acc += `/${part}`;
      segments.push({ label: part, path: acc });
    }
    return segments;
  }
}
