/**
 * App Help: first-open tour, `?` panel, EN/JA step resolution, 390px
 * no-overflow. `npx vitest run`
 *
 * The harness drives the component with a MemoryStorage stand-in (so the
 * first-open-once state is deterministic) and a small inline guide payload
 * (the same shape {% stx_help %} emits).
 */

import { beforeEach, describe, expect, it } from "vitest";

import {
  AppHelp,
  HELP_ATTRIBUTE,
  HELP_CHANGE,
  STORAGE_PREFIX,
  activeLanguage,
  loadGuide,
  stepText,
} from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/app-help";
import type { HelpStorage } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/app-help";

class MemoryStorage implements HelpStorage {
  private items = new Map<string, string>();
  getItem(key: string): string | null {
    return this.items.get(key) ?? null;
  }
  setItem(key: string, value: string): void {
    this.items.set(key, value);
  }
  removeItem(key: string): void {
    this.items.delete(key);
  }
}

const GUIDE = [
  { title: "Open a project", body: "Pick one from the header.", target: "#proj", icon: "📁" },
  { title: "Add a figure", body: "Use the toolbar.", target: "#add", icon: "＋" },
  { title: "About", body: "Plain help content (no target)." },
];

function mountGuide(app: string, lang: string, storage: HelpStorage, extra: Record<string, unknown> = {}): AppHelp {
  const root = document.createElement("div");
  root.setAttribute(HELP_ATTRIBUTE, app);
  document.body.appendChild(root);
  // the guide payload, as the {% stx_help %} tag emits it
  const script = document.createElement("script");
  script.type = "application/json";
  script.id = `stx-app-help-${app}`;
  script.textContent = JSON.stringify({ app, steps: GUIDE });
  document.body.appendChild(script);
  document.documentElement.setAttribute("lang", lang);
  return new AppHelp(root, { app, storage, ...extra });
}

beforeEach(() => {
  document.body.innerHTML = "";
  document.documentElement.setAttribute("lang", "en");
});

describe("guide loading", () => {
  it("reads the app's guide from its json_script element", () => {
    const storage = new MemoryStorage();
    mountGuide("scholar", "en", storage);
    const guide = loadGuide("scholar");
    expect(guide).not.toBeNull();
    expect(guide!.steps).toHaveLength(3);
  });

  it("returns null for an app with no guide payload", () => {
    expect(loadGuide("nobody")).toBeNull();
  });
});

describe("EN/JA step resolution", () => {
  it("uses the English text for an en document", () => {
    document.documentElement.setAttribute("lang", "en");
    expect(stepText({ en: "Open a project", ja: "プロジェクトを開く" }, activeLanguage())).toBe("Open a project");
  });

  it("uses the Japanese text for a ja document, falling back to English when missing", () => {
    document.documentElement.setAttribute("lang", "ja");
    expect(stepText({ en: "Open a project", ja: "プロジェクトを開く" }, "ja")).toBe("プロジェクトを開く");
    expect(stepText({ en: "Open a project" }, "ja")).toBe("Open a project");
  });

  it("treats a plain string as the text for every language", () => {
    expect(stepText("Same for all", "ja")).toBe("Same for all");
  });
});

describe("first-open tour runs once", () => {
  it("starts the tour on first open and does not restart after completion", () => {
    const storage = new MemoryStorage();
    const help = mountGuide("writer", "en", storage);
    // the component auto-starts the tour on a fresh storage (requestAnimationFrame is
    // not available in jsdom's default — drive it explicitly for determinism)
    help.startTour();
    expect(help.open).toBe(false); // the tour is not the panel
    expect(document.querySelector(".stx-app-help__tour")).not.toBeNull();

    help.closeTour();
    expect(document.querySelector(".stx-app-help__tour")).toBeNull();
    // first-open is now recorded
    expect(storage.getItem(`${STORAGE_PREFIX}writer:done`)).toBe("1");

    // a second fresh component must NOT auto-restart the tour
    const root2 = document.createElement("div");
    root2.setAttribute(HELP_ATTRIBUTE, "writer");
    document.body.appendChild(root2);
    const help2 = new AppHelp(root2, { app: "writer", storage });
    expect(document.querySelector(".stx-app-help__tour")).toBeNull();
  });

  it("advances and completes the tour step by step", () => {
    const storage = new MemoryStorage();
    const help = mountGuide("figrecipe", "en", storage);
    const changes: Array<{ view: string; step?: number }> = [];
    help.root.addEventListener(HELP_CHANGE, (e) => {
      changes.push((e as CustomEvent).detail);
    });
    help.startTour();
    // tour has 2 target-steps (the 3rd is plain panel content, skipped by the tour)
    expect(help.root.querySelectorAll(".stx-app-help__tour")).toHaveLength(1);
    help.nextTourStep();
    help.nextTourStep(); // on the last step, next() closes
    expect(document.querySelector(".stx-app-help__tour")).toBeNull();
    expect(changes.some((c) => c.view === "tour")).toBe(true);
    expect(changes.some((c) => c.view === "closed")).toBe(true);
  });

  it("highlights the step's target element", () => {
    const storage = new MemoryStorage();
    const target = document.createElement("button");
    target.id = "proj";
    target.textContent = "Project";
    document.body.appendChild(target);
    // give the target a layout box so getBoundingClientRect is non-zero
    target.getBoundingClientRect = () =>
      ({ left: 10, top: 20, width: 100, height: 44, right: 110, bottom: 64, x: 10, y: 20, toJSON: () => ({}) }) as DOMRect;
    const help = mountGuide("scholar", "en", storage);
    help.startTour();
    const highlight = document.querySelector(".stx-app-help__tour-highlight");
    expect(highlight).not.toBeNull();
  });
});

describe("the `?` help panel", () => {
  it("opens on the `?` button and lists every step", () => {
    const storage = new MemoryStorage();
    const help = mountGuide("scholar", "en", storage);
    help.openPanel();
    expect(help.open).toBe(true);
    const steps = document.querySelectorAll(".stx-app-help__step");
    expect(steps).toHaveLength(3);
  });

  it("closes on Escape", () => {
    const storage = new MemoryStorage();
    const help = mountGuide("scholar", "en", storage);
    help.openPanel();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(help.open).toBe(false);
  });

  it("offers replay, which restarts the tour", () => {
    const storage = new MemoryStorage();
    const help = mountGuide("scholar", "en", storage);
    help.openPanel();
    document.querySelector<HTMLButtonElement>(".stx-app-help__replay")?.click();
    expect(document.querySelector(".stx-app-help__tour")).not.toBeNull();
  });
});

/**
 * First use offers three choices, not two.
 *
 * SSOT: scitex-hub PR 923 §8 — "App first use may offer Watch tour, Later, and
 * Do not show again. These preferences are account-level and reversible in
 * Settings."
 *
 * The binary this replaces (`done` or not) cannot express the difference: a user
 * who answers "Later" has NOT seen the tour and has NOT refused it, and a
 * primitive that records both answers as one flag either nags a refuser forever
 * or silently loses the tour for someone who only postponed it.
 */
describe("first-use tour: Watch tour / Later / Do not show again", () => {
  it("records Later without claiming the guide was seen", () => {
    const storage = new MemoryStorage();
    const help = mountGuide("writer", "en", storage);
    help.deferTour();
    expect(storage.getItem(`${STORAGE_PREFIX}writer:tour`)).toBe("later");
  });

  it("records Do not show again as a refusal of its own", () => {
    const storage = new MemoryStorage();
    const help = mountGuide("writer", "en", storage);
    help.dismissTourForever();
    expect(storage.getItem(`${STORAGE_PREFIX}writer:tour`)).toBe("never");
  });

  it("reads back the three preferences, defaulting to unseen", () => {
    const storage = new MemoryStorage();
    const help = mountGuide("writer", "en", storage);
    expect(help.tourPreference()).toBe("unseen");
  });

  it("suppresses the auto-start after Later but keeps the two answers distinguishable", () => {
    const later = new MemoryStorage();
    mountGuide("writer", "en", later).deferTour();
    const root = document.createElement("div");
    root.setAttribute(HELP_ATTRIBUTE, "writer");
    document.body.appendChild(root);
    const reopened = new AppHelp(root, { app: "writer", storage: later });
    expect(reopened.tourPreference()).toBe("later");
  });

  it("never auto-starts again after Do not show again, and does not claim completion", () => {
    const storage = new MemoryStorage();
    mountGuide("writer", "en", storage).dismissTourForever();
    const root = document.createElement("div");
    root.setAttribute(HELP_ATTRIBUTE, "writer");
    document.body.appendChild(root);
    const reopened = new AppHelp(root, { app: "writer", storage });
    expect(reopened.tourPreference()).toBe("never");
  });

  it("offers a Settings-side reset that clears both keys, so the tour can be re-offered", () => {
    const storage = new MemoryStorage();
    const help = mountGuide("writer", "en", storage);
    help.dismissTourForever();
    help.resetTourPreference();
    expect(
      [storage.getItem(`${STORAGE_PREFIX}writer:tour`), storage.getItem(`${STORAGE_PREFIX}writer:done`)],
    ).toEqual([null, null]);
  });

  it("renders the three choices on the tour's first bubble with their own hooks", () => {
    const storage = new MemoryStorage();
    const help = mountGuide("writer", "en", storage);
    help.startTour();
    const classes = Array.from(document.querySelectorAll(".stx-app-help__choice")).map((n) =>
      Array.from(n.classList).filter((c) => c.startsWith("stx-app-help__choice--")).join(""),
    );
    expect(classes.sort()).toEqual([
      "stx-app-help__choice--later",
      "stx-app-help__choice--never",
      "stx-app-help__choice--watch",
    ]);
  });

  it("starts the tour when the user chooses Watch tour from the invite", () => {
    const storage = new MemoryStorage();
    const help = mountGuide("writer", "en", storage);
    help.showTourInvite();
    document.querySelector<HTMLButtonElement>(".stx-app-help__choice--watch")?.click();
    expect(document.querySelector(".stx-app-help__tour-bubble")).not.toBeNull();
  });
});

  it("asks on first use instead of starting the tour, and Watch then shows a highlight", () => {
    const storage = new MemoryStorage();
    const target = document.createElement("div");
    target.id = "proj";
    document.body.appendChild(target);
    const help = mountGuide("writer", "en", storage);
    help.showTourInvite();
    expect(document.querySelector(".stx-app-help__tour-highlight")).toBeNull();
  });

  it("highlights the first target only after Watch tour is chosen", () => {
    const storage = new MemoryStorage();
    const target = document.createElement("div");
    target.id = "proj";
    document.body.appendChild(target);
    const help = mountGuide("writer", "en", storage);
    help.showTourInvite();
    document.querySelector<HTMLButtonElement>(".stx-app-help__choice--watch")?.click();
    expect(document.querySelector(".stx-app-help__tour-highlight")).not.toBeNull();
  });
