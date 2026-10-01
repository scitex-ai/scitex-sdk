/**
 * Types for the in-app "How to use" primitive (app-help).
 *
 * One data source feeds BOTH the `?` help panel and the first-open coach-mark
 * tour: a small per-app steps file declared by the leaf app (JSON/YAML),
 * EN/JA. Leaves adopt by adding content + one template tag — no component
 * code. The component is CSS-first BEM (stx-app-help), self-contained like
 * app/panes.
 */

/** One step in the guide. `text` is EN/JA-able (see HelpStepText). */
export interface HelpStep {
  /** Stable id within the app's guide (used for storage / anchors). */
  id?: string;
  /** Step title. */
  title?: HelpStepText;
  /** Step body. */
  body?: HelpStepText;
  /**
   * Optional DOM selector to highlight for the first-open coach-mark. A step
   * with a `target` is a tour stop; one without is plain help content (shown
   * in the panel, skipped by the tour).
   */
  target?: string;
  /** Optional icon (text or emoji) shown beside the title. */
  icon?: string;
}

/**
 * A step's text, per language. Either a plain string (same for all languages)
 * or an object keyed by language code with an English fallback:
 *   "body": "Pick a project."                (all languages)
 *   "body": { "en": "Pick a project.", "ja": "プロジェクトを選択します。" }
 */
export type HelpStepText = string | Record<string, string>;

/** The per-app guide the component renders. */
export interface HelpGuide {
  /** App id (storage namespace); defaults to the root's data-stx-help. */
  app?: string;
  /** The ordered steps. */
  steps: HelpStep[];
}

/** The subset of Storage the component uses (tests pass a stand-in). */
export interface HelpStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/**
 * What the user answered at first use (SSOT: scitex-hub PR 923 §8 — "App first
 * use may offer Watch tour, Later, and Do not show again. These preferences are
 * account-level and reversible in Settings.").
 *
 * THREE STATES, not a boolean. "Later" means the user has NOT seen the tour and
 * has NOT refused it; "never" means they refused it. Collapsing both into the
 * existing `done` flag would either nag a refuser on every visit or silently
 * lose the tour for someone who only postponed it — and neither failure is
 * visible in the UI, only in the answer that went missing.
 */
export type TourPreference = "unseen" | "later" | "never";

/** Which of the three first-use choices was taken (the event payload). */
export type TourChoice = "watch" | "later" | "never";

export interface AppHelpOptions {
  /** Storage namespace / app id; defaults to the root's `data-stx-help`. */
  app?: string;
  /** Where the first-open state is kept; defaults to localStorage. */
  storage?: HelpStorage | null;
  /** Active language; defaults to the document's `<html lang>`, then "en". */
  language?: string;
  /** Suppress the automatic first-open tour (still allows open()/replay()). */
  autoStart?: boolean;
}

export interface HelpChangeDetail {
  app: string;
  /** "panel" | "tour" | "closed". */
  view: string;
  step?: number;
  /** Present when the change came from a first-use choice. */
  choice?: TourChoice;
}
