/**
 * scitex-ui client i18n — EN default, complete JA, follows the active language.
 *
 * Why a client dictionary rather than Django gettext: the shell's user-facing
 * strings are split across TWO render layers. The server template
 * (standalone_shell.html) is translatable with Django's {% translate %}, but the
 * strings rendered by the shared client components — app-launcher's "Apps" /
 * "No apps available", project-selector's "Select project" / "No projects" —
 * are built with document.createElement in the browser, where Django's
 * translation machinery does not reach. This module is the client half.
 *
 * SINGLE SOURCE OF TRUTH, deliberately: the English strings below are the
 * DEFAULT (a leaf that declares no language still gets correct English), and
 * Japanese is a complete second column. Selecting is by the document's active
 * language, which is already correct upstream — the shell renders
 * <html lang="{{ shell_lang }}"> from the host's active language
 * (branding._active_language), and test_html_lang_follows_the_active_language
 * pins that. So a mounted leaf that follows the host language picks the right
 * column here with no extra wiring; a standalone leaf whose host is English
 * gets the English default.
 *
 * The key set is kept small and shared with the server catalog on purpose
 * (the same few shell strings must read identically whether the template or a
 * component renders them); tests/develop/test_shell_i18n.py cross-checks the
 * key set, the completeness of the ja column, and that the components actually
 * route their defaults through this helper rather than re-hardcoding them.
 */

/** Languages this dictionary ships. EN is the default; JA is complete. */
export const I18N_LANGUAGES = ["en", "ja"] as const;
export type I18NLanguage = (typeof I18N_LANGUAGES)[number];

/** The shared shell strings, keyed once, written in both languages. */
export const SHELL_STRINGS = {
  en: {
    apps: "Apps",
    noAppsAvailable: "No apps available",
    selectProject: "Select project",
    noProjects: "No projects",
  },
  ja: {
    apps: "アプリ",
    noAppsAvailable: "利用可能なアプリがありません",
    selectProject: "プロジェクトを選択してください",
    noProjects: "プロジェクトがありません",
  },
} as const;

export type ShellStringKey = keyof (typeof SHELL_STRINGS)["en"];

function normalize(lang: string | null | undefined): I18NLanguage {
  if (!lang) return "en";
  const code = lang.trim().toLowerCase();
  if (code === "ja" || code.startsWith("ja-")) return "ja";
  return "en"; // EN is the default for every other (and malformed) tag.
}

/**
 * Translate one shared shell string into the document's active language.
 *
 * @param key one of SHELL_STRINGS' keys
 * @param doc the document to read the active language from (defaults to the
 *            global document; injectable so tests can exercise both languages
 *            without mutating a real DOM).
 * @returns the English string when the active language is not one we ship.
 */
export function shellTranslate(
  key: ShellStringKey,
  doc: { documentElement?: { lang?: string } } = document,
): string {
  const lang = normalize(doc?.documentElement?.lang);
  return SHELL_STRINGS[lang][key] ?? SHELL_STRINGS.en[key];
}
