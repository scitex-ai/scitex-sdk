/** Native section anchors with shared underline styling and passive current tracking. */
type Item = { link: HTMLAnchorElement; section: HTMLElement };
const instances = new WeakMap<HTMLElement, SectionNav>();

function sectionFor(hash: string): HTMLElement | null {
  try {
    const target = document.getElementById(decodeURIComponent(hash.slice(1)));
    return target?.closest<HTMLElement>("section, [data-stx-section]") ?? null;
  } catch {
    return null; // Malformed percent escapes never become selectors or requests.
  }
}

export class SectionNav {
  private items: Item[] = [];
  private frame = 0;
  private useHash = false;
  private observer: ResizeObserver | null = null;

  constructor(private readonly element: HTMLElement) {
    this.refresh();
    window.addEventListener("scroll", this.onGeometry, { capture: true, passive: true });
    window.addEventListener("resize", this.onGeometry);
    window.addEventListener("hashchange", this.onHistory);
    window.addEventListener("popstate", this.onHistory);
    window.visualViewport?.addEventListener("resize", this.onGeometry);
    if (typeof ResizeObserver !== "undefined") {
      this.observer = new ResizeObserver(this.onGeometry);
      this.observer.observe(element);
      for (const header of document.querySelectorAll("header")) this.observer.observe(header);
    }
    element.setAttribute("data-stx-section-nav-mounted", "");
    this.schedule(true);
  }

  /** Re-read native links after an owner deliberately updates navigation content. */
  refresh(): void {
    this.items = [];
    for (const link of this.element.querySelectorAll<HTMLAnchorElement>("a[href]")) {
      let url: URL;
      try { url = new URL(link.href, document.baseURI); }
      catch { continue; }
      if (url.origin !== location.origin || url.pathname !== location.pathname || url.search !== location.search || !url.hash) continue;
      const section = sectionFor(url.hash);
      if (section) this.items.push({ link, section });
    }
    this.schedule(false);
  }

  private onGeometry = (): void => this.schedule(false);
  private onHistory = (): void => this.schedule(true);

  private schedule(fromHash: boolean): void {
    this.useHash ||= fromHash;
    if (this.frame) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = 0;
      const useHash = this.useHash;
      this.useHash = false;
      this.update(useHash);
    });
  }

  private update(useHash: boolean): void {
    if (!this.items.length) return;
    const ordered = this.items.map(item => ({ item, rect: item.section.getBoundingClientRect() }))
      .filter(({ rect }) => rect.height > 0)
      .sort((a, b) => a.rect.top - b.rect.top);
    if (!ordered.length) return;
    const hashSection = useHash ? sectionFor(location.hash) : null;
    let selected = hashSection && this.items.some(item => item.section === hashSection) ? hashSection : null;
    if (!selected) {
      const line = Math.max(0, Math.min(innerHeight - 1, this.element.getBoundingClientRect().bottom + 1));
      const passed = ordered.filter(({ item, rect }) => {
        // Native anchors settle at scroll-margin-top, which can intentionally
        // leave more heading clearance than the sticky navigator alone.
        const margin = Number.parseFloat(getComputedStyle(item.section).scrollMarginTop);
        const boundary = Number.isFinite(margin) ? Math.max(line, margin + 1) : line;
        return rect.top <= boundary;
      });
      selected = (passed.at(-1) ?? ordered[0]).item.section;
      const height = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
      if (height > innerHeight + 1 && scrollY + innerHeight >= height - 2) selected = ordered.at(-1)!.item.section;
    }
    let marked = false;
    for (const { link, section } of this.items) {
      if (section === selected && !marked) {
        link.setAttribute("aria-current", "location");
        marked = true;
      } else link.removeAttribute("aria-current");
    }
  }

  destroy(): void {
    cancelAnimationFrame(this.frame);
    window.removeEventListener("scroll", this.onGeometry, true);
    window.removeEventListener("resize", this.onGeometry);
    window.removeEventListener("hashchange", this.onHistory);
    window.removeEventListener("popstate", this.onHistory);
    window.visualViewport?.removeEventListener("resize", this.onGeometry);
    this.observer?.disconnect();
    this.element.removeAttribute("data-stx-section-nav-mounted");
    instances.delete(this.element);
  }
}

export function mountSectionNavs(root: ParentNode = document): SectionNav[] {
  const elements = Array.from(root.querySelectorAll<HTMLElement>("[data-stx-section-nav]"));
  if (root instanceof HTMLElement && root.matches("[data-stx-section-nav]")) elements.unshift(root);
  return elements.map(element => {
    const existing = instances.get(element);
    if (existing) return existing;
    const controller = new SectionNav(element);
    instances.set(element, controller);
    return controller;
  });
}
