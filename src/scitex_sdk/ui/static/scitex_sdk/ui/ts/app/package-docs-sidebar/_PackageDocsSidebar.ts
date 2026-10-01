/**
 * PackageDocsSidebar — navigable sidebar for SciTeX package documentation.
 *
 * Usage:
 *   import { PackageDocsSidebar } from 'scitex_sdk/ui/ts/app/package-docs-sidebar';
 *   const sidebar = new PackageDocsSidebar({
 *     container: '#pkg-sidebar',
 *     apiUrl: '/apps/docs/api/packages/',
 *     onPackageSelect: (pkg) => console.log(pkg.name),
 *   });
 */

import { BaseComponent } from "../../_base/BaseComponent";
import type { PackageInfo, PackageDocsSidebarConfig } from "./types";

const CLS = "stx-app-pkg-sidebar";

export class PackageDocsSidebar extends BaseComponent<PackageDocsSidebarConfig> {
  private packages: PackageInfo[] = [];

  constructor(config: PackageDocsSidebarConfig) {
    super(config);
    if (config.apiUrl) {
      this.fetchPackages(config.apiUrl);
    }
  }

  setData(packages: PackageInfo[]): void {
    this.packages = packages;
    this.render();
  }

  async refresh(): Promise<void> {
    if (this.config.apiUrl) {
      await this.fetchPackages(this.config.apiUrl);
    } else {
      this.render();
    }
  }

  select(name: string): void {
    const cls = `${CLS}__item--active`;
    this.container.querySelectorAll(`.${CLS}__item`).forEach((el) => {
      el.classList.toggle(
        cls,
        (el as HTMLElement).getAttribute("data-name") === name,
      );
    });
  }

  override destroy(): void {
    this.packages = [];
    super.destroy();
  }

  private async fetchPackages(url: string): Promise<void> {
    this.container.innerHTML =
      `<div class="${CLS}__loading">` +
      `<i class="fas fa-spinner fa-spin"></i> Loading packages...` +
      `</div>`;
    try {
      const resp = await fetch(url);
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
      }
      const data = await resp.json();
      this.packages = Array.isArray(data) ? data : (data.packages ?? []);
      this.render();
    } catch (err) {
      this.container.innerHTML =
        `<div class="${CLS}__error">` +
        `<i class="fas fa-exclamation-triangle"></i> ${err instanceof Error ? err.message : "Failed to load packages"}` +
        `</div>`;
    }
  }

  private render(): void {
    this.container.innerHTML = "";
    const nav = document.createElement("nav");
    nav.className = CLS;

    const groups = new Map<string, PackageInfo[]>();
    for (const pkg of this.packages) {
      const group = pkg.group ?? "Other";
      if (!groups.has(group)) groups.set(group, []);
      groups.get(group)!.push(pkg);
    }

    for (const [groupName, pkgs] of groups) {
      const header = document.createElement("div");
      header.className = `${CLS}__group-header`;
      header.textContent = groupName;
      nav.appendChild(header);

      for (const pkg of pkgs) {
        const item = document.createElement("a");
        item.className = `${CLS}__item`;
        item.setAttribute("data-name", pkg.name);
        if (pkg.url) item.href = pkg.url;

        const icon = document.createElement("i");
        icon.className = pkg.icon ?? "fas fa-cube";
        item.appendChild(icon);

        const label = document.createElement("span");
        label.className = `${CLS}__label`;
        label.textContent = pkg.name;
        item.appendChild(label);

        const version = document.createElement("span");
        version.className = `${CLS}__version`;
        version.textContent = pkg.version;
        item.appendChild(version);

        item.addEventListener("click", (e) => {
          if (this.config.onPackageSelect) {
            e.preventDefault();
            this.container
              .querySelectorAll(`.${CLS}__item`)
              .forEach((el) => el.classList.remove(`${CLS}__item--active`));
            item.classList.add(`${CLS}__item--active`);
            this.config.onPackageSelect(pkg);
          }
        });

        nav.appendChild(item);
      }
    }

    this.container.appendChild(nav);
  }
}
