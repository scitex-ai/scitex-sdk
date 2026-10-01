/**
 * Types for the bilingual tour player (app/tour-player).
 *
 * SSOT: scitex-hub PR 923 §8. The player is SDK-side and generic: it renders
 * whatever tracks and chapters the host declares. Which tours exist, when a tour
 * is offered, and what the recordings say are the host's and the video pipeline's
 * business (hub owns policy/content; the video agent owns the recordings).
 */

/** One selectable rendition. `lang` is a BCP-47 base tag, e.g. "en" | "ja". */
export interface TourTrack {
  lang: string;
  src: string;
  /** Human label for the menu; defaults to the language tag. */
  label?: string;
}

/** A chapter marker. `start` is seconds into the recording. */
export interface TourChapter {
  title: string;
  /** Start offset in seconds. Chapters are ordered by this at render time. */
  start: number;
  /** Optional stable hook for the recording pipeline (never the title). */
  id?: string;
}

export interface TourPlayerOptions {
  /** App/player id, used in the change event and for storage namespacing. */
  app?: string;
  /** Audio renditions. The first is the default unless `audioLanguage` says otherwise. */
  audio: TourTrack[];
  /** Subtitle renditions (WebVTT). None of them are enabled until asked for. */
  subtitles: TourTrack[];
  /** Chapter markers; defaults to none (no chapter UI). */
  chapters?: TourChapter[];
  /** Default audio language; defaults to the first audio track. */
  audioLanguage?: string;
  /** Default caption language; defaults to "off" so a tour does not start captioned. */
  captionLanguage?: string;
  /** Begin playing on mount. Defaults to FALSE: a tour is an offer, not an interruption. */
  autoplay?: boolean;
}

export interface TourPlayerChangeDetail {
  app: string;
  /** "audio-language" | "caption-language" | "chapter" | "play" | "pause". */
  change: string;
  /** The new language for the two language changes. */
  language?: string;
  /** The chapter index for "chapter". */
  index?: number;
  /** Seconds, at the moment of the change. */
  time: number;
}
