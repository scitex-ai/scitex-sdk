/**
 * File Upload Handler - Uses adapter instead of hardcoded URLs
 * Ported from scitex-cloud
 */

import type { TreeConfig } from "../types";

export class FileUpload {
  private config: TreeConfig;
  private refresh: () => Promise<void>;
  private showMessage: (
    message: string,
    type: "success" | "error" | "info",
  ) => void;

  constructor(
    config: TreeConfig,
    refresh: () => Promise<void>,
    showMessage?: (message: string, type: "success" | "error" | "info") => void,
  ) {
    this.config = config;
    this.refresh = refresh;
    this.showMessage =
      showMessage ||
      ((msg, type) => console.log(`[FileUpload] ${type}: ${msg}`));
  }

  async uploadFiles(files: FileList, targetPath: string): Promise<void> {
    const adapter = this.config.adapter;
    if (!adapter.uploadFile) {
      this.showMessage("Upload not supported", "error");
      return;
    }

    const fileCount = files.length;
    this.showMessage(
      `Uploading ${fileCount} file${fileCount > 1 ? "s" : ""}...`,
      "info",
    );
    let successCount = 0;
    let errorCount = 0;

    for (const file of Array.from(files)) {
      try {
        const path = targetPath ? `${targetPath}/${file.name}` : file.name;
        const data = await adapter.uploadFile(file, path);
        if (data.success) successCount++;
        else errorCount++;
      } catch {
        errorCount++;
      }
    }
    if (successCount > 0) {
      await this.refresh();
      this.showMessage(
        `Uploaded ${successCount} file${successCount > 1 ? "s" : ""}${errorCount > 0 ? ` (${errorCount} failed)` : ""}`,
        errorCount > 0 ? "info" : "success",
      );
    } else {
      this.showMessage("Failed to upload files", "error");
    }
  }

  isDownloadableUrl(url: string): boolean {
    if (!url.startsWith("http://") && !url.startsWith("https://")) return false;
    return true;
  }

  async downloadAndUploadFromUrl(
    url: string,
    targetPath: string,
  ): Promise<void> {
    const adapter = this.config.adapter;
    if (!adapter.uploadFromUrl) {
      this.showMessage("URL upload not supported", "error");
      return;
    }

    this.showMessage("Downloading...", "info");
    try {
      let fileName = url.split("/").pop()?.split("?")[0] || "download";
      if (!fileName.includes(".")) fileName += ".bin";
      const path = targetPath ? `${targetPath}/${fileName}` : fileName;
      const data = await adapter.uploadFromUrl(url, path);
      if (data.success) {
        this.showMessage(`Saved as ${data.path}`, "success");
        await this.refresh();
      } else {
        this.showMessage(`Failed: ${data.error}`, "error");
      }
    } catch {
      this.showMessage("Failed to download", "error");
    }
  }
}
