/**
 * Tour player — the bilingual tour video primitive.
 *
 *   import { TourPlayer } from "scitex-ui/ts/app/tour-player";
 *
 *   const player = new TourPlayer(root, {
 *     app: "demo",
 *     audio: [{ lang: "en", src: "/media/tour-en.mp4" }, { lang: "ja", src: "/media/tour-ja.mp4" }],
 *     subtitles: [{ lang: "en", src: "/media/tour-en.vtt" }, { lang: "ja", src: "/media/tour-ja.vtt" }],
 *     chapters: [{ title: "Create a project", start: 0 }],
 *   });
 *
 * Styling: `css/app/tour-player.css`. Pre-built: `js/app/tour-player.js`.
 */

export { TourPlayer, PLAYER_ACTS, PLAYER_ATTRIBUTE, PLAYER_CHANGE } from "./_TourPlayer";
export type { TourChapter, TourPlayerChangeDetail, TourPlayerOptions, TourTrack } from "./types";
