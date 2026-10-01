/**
 * TreeMessageHandler - Message notification for file tree
 * Ported from scitex-cloud (no API deps)
 */

export function showTreeMessage(
  message: string,
  type: "success" | "error" | "info",
): void {
  if ((window as any).SciTeX?.notify) {
    (window as any).SciTeX.notify(message, type);
    return;
  }

  window.dispatchEvent(
    new CustomEvent("wft-message", {
      detail: { message, type },
    }),
  );

  const logMethod =
    type === "error" ? "error" : type === "success" ? "log" : "info";
  console[logMethod](`[WorkspaceFilesTree] ${message}`);
}
