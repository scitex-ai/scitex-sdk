/**
 * TreeFileOperations - Uses adapter instead of hardcoded URLs
 * Ported from scitex-cloud
 */
import type { TreeConfig } from "../types";

export class TreeFileOperations {
  constructor(
    private config: TreeConfig,
    private refresh: () => Promise<void>,
    private showMessage: (
      message: string,
      type: "success" | "error" | "info",
    ) => void,
    private stateManagerExpand: (path: string) => void,
  ) {}

  downloadFile(filePath: string): void {
    const adapter = this.config.adapter;
    if (adapter.getFileUrl) {
      const url = adapter.getFileUrl(filePath);
      const link = document.createElement("a");
      link.href = url;
      link.download = filePath.split("/").pop() || "download";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      this.showMessage("Download not supported", "error");
    }
  }

  async promptCreateSymlink(sourcePath: string): Promise<void> {
    const adapter = this.config.adapter;
    if (!adapter.createSymlink) {
      this.showMessage("Symlink not supported", "error");
      return;
    }
    const parts = sourcePath.split("/");
    const fileName = parts.pop() || sourcePath;
    const parentPath = parts.join("/");
    const symlinkName = `${fileName}.symlink`;
    const targetPath = parentPath
      ? `${parentPath}/${symlinkName}`
      : symlinkName;
    try {
      const data = await adapter.createSymlink(sourcePath, targetPath);
      if (data.success) {
        this.showMessage(`Created ${symlinkName} - drag to move`, "success");
        await this.refresh();
      } else {
        this.showMessage(`Failed: ${data.error}`, "error");
      }
    } catch {
      this.showMessage("Failed to create symlink", "error");
    }
  }

  async extractBundle(bundlePath: string): Promise<void> {
    const adapter = this.config.adapter;
    if (!adapter.extractBundle) {
      this.showMessage("Extract not supported", "error");
      return;
    }
    const outputPath = bundlePath + ".d";
    const bundleName = bundlePath.split("/").pop() || "bundle";
    try {
      const data = await adapter.extractBundle(bundlePath, outputPath);
      if (data.success) {
        this.showMessage(
          `Extracted ${bundleName} to ${bundleName}.d`,
          "success",
        );
        await this.refresh();
        this.stateManagerExpand(outputPath);
      } else {
        this.showMessage(`Failed: ${data.error}`, "error");
      }
    } catch {
      this.showMessage("Failed to extract bundle", "error");
    }
  }
}
