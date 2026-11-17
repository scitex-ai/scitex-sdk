/* AUTO-GENERATED from ts/app/creator-wizard.ts via esbuild — do not edit by hand. Rebuild: npm run build:ui -- --only js/app/creator-wizard.js */

// ts/_base/csrf.ts
function csrfToken() {
  if (typeof document === "undefined") return "";
  const rendered = document.querySelector(
    'input[name="csrfmiddlewaretoken"]'
  )?.value;
  if (rendered) return rendered;
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

// ts/app/creator-wizard.ts
async function post(path, body, outId) {
  const out = document.getElementById(outId);
  if (!out) return;
  out.textContent = "Working\u2026";
  try {
    const response = await fetch(path, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      body: JSON.stringify(body)
    });
    const data = await response.json();
    const lines = [];
    if (data.success === true) {
      lines.push("Done.");
      if (data.project_dir) lines.push("Project: " + data.project_dir);
      if (data.files) lines.push(data.files.length + " file(s) scaffolded.");
      if (data.pr_url) lines.push("PR: " + data.pr_url);
      if (data.module_name) lines.push("Module: " + data.module_name);
    } else if (data.ok === true) {
      lines.push("Input is valid.");
    } else {
      for (const error of data.errors || ["Unknown error"]) lines.push("\u2717 " + error);
    }
    for (const warning of data.warnings || []) lines.push("! " + warning);
    out.textContent = lines.join("\n");
  } catch (error) {
    out.textContent = "Request failed: " + error;
  }
}
function val(id) {
  return document.querySelector("#" + id)?.value || "";
}
function brief() {
  return {
    label: val("stx-label"),
    description: val("stx-description"),
    starter: document.querySelector('input[name="starter"]:checked')?.value || ""
  };
}
document.getElementById("stx-check-input")?.addEventListener("click", () => {
  void post("api/validate-input", brief(), "stx-create-result");
});
document.getElementById("stx-create")?.addEventListener("click", () => {
  void post("api/create", { ...brief(), target_dir: val("stx-target") }, "stx-create-result");
});
document.getElementById("stx-validate")?.addEventListener("click", () => {
  void post("api/validate-app", { app_dir: val("stx-appdir") }, "stx-validate-result");
});
for (const [id, path] of [["stx-dev-install", "api/dev-install"], ["stx-publish", "api/publish"]]) {
  document.getElementById(id)?.addEventListener("click", () => {
    void post(path, { app_dir: val("stx-appdir"), server_url: val("stx-server"), token: val("stx-token") }, "stx-cloud-result");
  });
}
function placePicker() {
  const picker = document.querySelector("[data-stx-project-picker]");
  if (!picker) return;
  window.stxAppHeader?.get()?.projectSlot?.appendChild(picker);
  picker.addEventListener("stx-project-selector:change", (event) => {
    const detail = event.detail;
    const target = document.querySelector("#stx-target");
    if (detail?.id && detail.name && target) {
      if (!target.value) target.value = detail.name;
      target.placeholder = "Resuming: " + detail.name + " (edit as needed)";
    }
  });
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", placePicker);
else placePicker();
