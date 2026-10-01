/**
 * Entry for the pre-built `js/app/tour-player.js`.
 *
 * A page declares the renditions it has in a json_script element and the player
 * mounts itself on every `[data-stx-tour-player]` element that does not have one
 * yet. Self-guards: no container, no player.
 */

import { PLAYER_ATTRIBUTE, TourPlayer } from "./_TourPlayer";
import type { TourPlayerOptions } from "./types";

export * from "./index";

export const SCRIPT_ID_PREFIX = "stx-tour-player-";

/** The declared payload for an app, as its json_script element carries it. */
export function loadPlayerOptions(app: string, doc: Document = document): TourPlayerOptions | null {
  const script = doc.getElementById(`${SCRIPT_ID_PREFIX}${app}`);
  if (!script?.textContent) return null;
  try {
    return JSON.parse(script.textContent) as TourPlayerOptions;
  } catch {
    return null;
  }
}

/** Mount a player on every declared container that does not have one. */
export function mountTourPlayers(doc: Document = document): TourPlayer[] {
  const mounted: TourPlayer[] = [];
  doc.querySelectorAll<HTMLElement>(`[${PLAYER_ATTRIBUTE}]`).forEach((root) => {
    if (root.querySelector(".stx-tour-player__video")) return; // already mounted
    const app = root.getAttribute(PLAYER_ATTRIBUTE) ?? "tour";
    const options = loadPlayerOptions(app, doc);
    if (!options) return;
    mounted.push(new TourPlayer(root, { ...options, app }));
  });
  return mounted;
}

declare global {
  interface Window {
    stxTourPlayer?: {
      TourPlayer: typeof TourPlayer;
      mountTourPlayers: typeof mountTourPlayers;
      loadPlayerOptions: typeof loadPlayerOptions;
    };
  }
}

export const stxTourPlayer = { TourPlayer, mountTourPlayers, loadPlayerOptions };

if (typeof window !== "undefined") {
  window.stxTourPlayer = stxTourPlayer;
  const autoMount = (): void => {
    mountTourPlayers();
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoMount);
  } else {
    autoMount();
  }
}
