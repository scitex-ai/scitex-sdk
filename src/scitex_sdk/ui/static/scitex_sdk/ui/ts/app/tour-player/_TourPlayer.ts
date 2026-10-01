/**
 * TourPlayer — the bilingual tour player primitive.
 *
 * SSOT: scitex-hub PR 923 §8. The two behaviours this exists for:
 *
 *  1. SWITCHING A LANGUAGE MUST NOT LOSE THE VIEWER'S PLACE. Position and play
 *     state are captured before the source swap and restored after it — once
 *     immediately, and once on `loadedmetadata`, because a seek assigned before
 *     metadata arrives is discarded by the media element. Restoring only on the
 *     event means the position is silently wrong in the window before it fires;
 *     restoring only immediately means it is wrong whenever it does.
 *
 *  2. THE RECORDING PIPELINE LOCATES CONTROLS BY DATA ATTRIBUTE, NOT BY LABEL.
 *     §8 drives ONE action timeline to produce both the EN and the JA recording,
 *     so a locator containing prose cannot survive the second locale. Every
 *     control publishes `data-stx-player-act`.
 *
 * The audio and subtitle choices are independent: JA audio with EN subtitles is a
 * normal preference, so setting one never resets the other.
 *
 * Self-contained like app/panes and app/app-help: BEM `stx-tour-player`, vanilla
 * TS, no framework, no dependencies.
 */

import { gettext } from "../../_base/gettext";
import type { TourChapter, TourPlayerChangeDetail, TourPlayerOptions, TourTrack } from "./types";

export const PLAYER_ATTRIBUTE = "data-stx-tour-player";
export const PLAYER_CHANGE = "stx-tour-player:change";

/** The hook vocabulary. Stable: the recording pipeline drives these, and a
 *  label-based locator would break the moment the UI is translated. */
export const PLAYER_ACTS = {
  playPause: "play-pause",
  prevChapter: "prev-chapter",
  nextChapter: "next-chapter",
  audioLanguage: "audio-language",
  captionLanguage: "caption-language",
} as const;

const CLS = "stx-tour-player";
const CLS_VIDEO = `${CLS}__video`;
const CLS_CONTROLS = `${CLS}__controls`;
const CLS_CONTROL = `${CLS}__control`;
const CLS_CHAPTERS = `${CLS}__chapters`;
const CLS_CHAPTER = `${CLS}__chapter`;

export class TourPlayer {
  readonly root: HTMLElement;
  readonly app: string;
  private readonly audio: TourTrack[];
  private readonly subtitles: TourTrack[];
  private readonly chapterList: TourChapter[];
  private readonly video: HTMLVideoElement;
  private controls: HTMLElement | null = null;
  private chapterRow: HTMLElement | null = null;
  private activeAudio: string;
  private activeCaption: string;
  /** Set while a source swap is in flight, so the metadata handler can restore. */
  private restoringTo: number | null = null;
  private resumeAfterSwitch = false;

  constructor(root: HTMLElement, options: TourPlayerOptions) {
    this.root = root;
    this.app = options.app ?? root.getAttribute(PLAYER_ATTRIBUTE) ?? "tour";
    this.audio = options.audio ?? [];
    this.subtitles = options.subtitles ?? [];
    this.chapterList = [...(options.chapters ?? [])].sort((a, b) => a.start - b.start);
    this.activeAudio = options.audioLanguage ?? this.audio[0]?.lang ?? "en";
    // Captions start OFF: a tour that begins captioned has made a choice the
    // viewer did not, and the viewer who needs them will turn them on.
    this.activeCaption = options.captionLanguage ?? "off";

    root.classList.add(CLS);

    this.video = document.createElement("video");
    this.video.className = CLS_VIDEO;
    this.video.setAttribute("playsinline", "");
    this.video.preload = "metadata";
    this.video.controls = false; // the primitive owns the control row (§8 hooks)
    const initial = this.track(this.audio, this.activeAudio);
    if (initial) this.video.src = initial.src;
    for (const track of this.subtitles) {
      const el = document.createElement("track");
      el.kind = "subtitles";
      el.src = track.src;
      el.srclang = track.lang;
      el.label = track.label ?? track.lang;
      el.default = track.lang === this.activeCaption;
      this.video.appendChild(el);
    }
    this.video.addEventListener("loadedmetadata", () => {
      if (this.restoringTo === null) return;
      const target = this.restoringTo;
      this.restoringTo = null;
      // The seek only sticks once the media element knows its duration.
      try {
        this.video.currentTime = target;
      } catch {
        /* not seekable yet; the position was already applied once */
      }
      if (this.resumeAfterSwitch) {
        this.resumeAfterSwitch = false;
        this.play();
      }
    });
    root.appendChild(this.video);

    this.controls = this.renderControls();
    root.appendChild(this.controls);
    if (this.chapterList.length > 0) {
      this.chapterRow = this.renderChapters();
      root.appendChild(this.chapterRow);
    }
    this.applyCaptionTracks();
    // Paint the initial state of the two language controls. Without this the
    // caption button reads as an empty box until the first interaction, which is
    // exactly the wrong moment to be unlabelled: a viewer looking for subtitles
    // finds a blank control and concludes there are none.
    this.refreshControls();
    if (options.autoplay) this.play();
  }

  get audioLanguage(): string {
    return this.activeAudio;
  }

  get captionLanguage(): string {
    return this.activeCaption;
  }

  get currentTime(): number {
    return this.video.currentTime;
  }

  set currentTime(seconds: number) {
    // Assigning before metadata is available throws in some browsers; the value
    // is still observable on the element, which is what the position contract is
    // about, so the failure is contained rather than propagated to the caller.
    try {
      this.video.currentTime = seconds;
    } catch {
      /* nothing to do: the position will be re-applied on loadedmetadata */
    }
  }

  get chapters(): TourChapter[] {
    return [...this.chapterList];
  }

  get isPlaying(): boolean {
    return !this.video.paused && !this.video.ended;
  }

  /**
   * Switch the audio rendition, keeping the viewer where they were.
   *
   * `wasPlaying` lets a caller that already knows the play state pass it in;
   * otherwise it is read from the element BEFORE the swap, because swapping a
   * source resets `paused` and reading it afterwards would always look stopped.
   */
  setAudioLanguage(lang: string, options: { wasPlaying?: boolean } = {}): void {
    const track = this.track(this.audio, lang);
    if (!track) return;
    const resumeAt = this.video.currentTime;
    const wasPlaying = options.wasPlaying ?? this.isPlaying;
    this.activeAudio = lang;
    this.restoringTo = resumeAt;
    this.resumeAfterSwitch = wasPlaying;
    this.video.src = track.src;
    // Applied immediately as well as on loadedmetadata: an immediate assignment
    // is what the element can observe now, and the event is what makes it stick.
    this.currentTime = resumeAt;
    this.applyCaptionTracks();
    this.refreshControls();
    if (wasPlaying) this.play();
    this.emit({ change: "audio-language", language: lang, time: resumeAt });
  }

  /** Switch the caption rendition. Captions are a separate track set, so this
   *  never touches the media source and therefore cannot move the position. */
  setCaptionLanguage(lang: string): void {
    const next = lang === "off" || this.track(this.subtitles, lang) ? lang : this.activeCaption;
    this.activeCaption = next;
    this.applyCaptionTracks();
    this.refreshControls();
    this.emit({ change: "caption-language", language: next, time: this.video.currentTime });
  }

  goToChapter(index: number): void {
    const chapter = this.chapterList[index];
    if (!chapter) return;
    this.currentTime = chapter.start;
    this.refreshControls();
    this.emit({ change: "chapter", index, time: chapter.start });
  }

  play(): void {
    const result = this.video.play() as Promise<void> | undefined;
    // jsdom has no media pipeline and a headless browser may still refuse
    // autoplay; a rejected promise here is not a reason to break the caller.
    if (result && typeof result.catch === "function") result.catch(() => undefined);
    this.refreshControls();
  }

  pause(): void {
    this.video.pause();
    this.refreshControls();
    this.emit({ change: "pause", time: this.video.currentTime });
  }

  toggle(): void {
    if (this.isPlaying) this.pause();
    else this.play();
  }

  destroy(): void {
    this.video.pause();
    this.root.innerHTML = "";
    this.root.classList.remove(CLS);
  }

  private track(tracks: TourTrack[], lang: string): TourTrack | undefined {
    return tracks.find((t) => t.lang === lang);
  }

  private applyCaptionTracks(): void {
    const tracks = this.video.textTracks;
    if (!tracks) return;
    for (let i = 0; i < tracks.length; i += 1) {
      const track = tracks[i];
      if (!track) continue;
      const wanted = this.activeCaption !== "off" && track.language === this.activeCaption;
      track.mode = wanted ? "showing" : "disabled";
    }
  }

  private renderControls(): HTMLElement {
    const row = document.createElement("div");
    row.className = CLS_CONTROLS;

    const make = (act: string, label: string, onClick: () => void): HTMLButtonElement => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `${CLS_CONTROL} ${CLS_CONTROL}--${act}`;
      button.dataset.stxPlayerAct = act;
      button.setAttribute("aria-label", label);
      button.addEventListener("click", onClick);
      return button;
    };

    row.appendChild(
      make(PLAYER_ACTS.playPause, gettext("Play"), () => this.toggle()),
    );
    if (this.chapterList.length > 0) {
      row.appendChild(
        make(PLAYER_ACTS.prevChapter, gettext("Previous chapter"), () => this.stepChapter(-1)),
      );
      row.appendChild(
        make(PLAYER_ACTS.nextChapter, gettext("Next chapter"), () => this.stepChapter(1)),
      );
    }
    if (this.audio.length > 0) {
      row.appendChild(
        make(PLAYER_ACTS.audioLanguage, gettext("Audio language"), () => this.cycleAudio()),
      );
    }
    if (this.subtitles.length > 0) {
      row.appendChild(
        make(PLAYER_ACTS.captionLanguage, gettext("Subtitles"), () => this.cycleCaptions()),
      );
    }
    return row;
  }

  private renderChapters(): HTMLElement {
    const row = document.createElement("div");
    row.className = CLS_CHAPTERS;
    row.setAttribute("role", "list");
    this.chapterList.forEach((chapter, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = CLS_CHAPTER;
      // The chapter's own hook is its INDEX or declared id, never its title:
      // the pipeline has to find the same marker in the EN and the JA recording.
      button.dataset.stxPlayerChapter = chapter.id ?? String(index);
      button.setAttribute("role", "listitem");
      button.textContent = chapter.title;
      button.addEventListener("click", () => this.goToChapter(index));
      row.appendChild(button);
    });
    return row;
  }

  private stepChapter(direction: number): void {
    const next = Math.min(
      Math.max(this.currentChapterIndex() + direction, 0),
      this.chapterList.length - 1,
    );
    this.goToChapter(next);
  }

  private currentChapterIndex(): number {
    let index = 0;
    this.chapterList.forEach((chapter, i) => {
      if (this.video.currentTime >= chapter.start) index = i;
    });
    return index;
  }

  private cycleAudio(): void {
    if (this.audio.length === 0) return;
    const current = this.audio.findIndex((t) => t.lang === this.activeAudio);
    const next = this.audio[(current + 1) % this.audio.length];
    if (next) this.setAudioLanguage(next.lang);
  }

  private cycleCaptions(): void {
    const langs = ["off", ...this.subtitles.map((t) => t.lang)];
    const current = langs.indexOf(this.activeCaption);
    this.setCaptionLanguage(langs[(current + 1) % langs.length] ?? "off");
  }

  /** Reflect the state on the controls: labels and `aria-pressed` are the only
   *  things that change, so the hooks stay stable for the pipeline. */
  private refreshControls(): void {
    if (!this.controls) return;
    const play = this.controls.querySelector<HTMLButtonElement>(
      `[data-stx-player-act="${PLAYER_ACTS.playPause}"]`,
    );
    if (play) play.setAttribute("aria-label", this.isPlaying ? gettext("Pause") : gettext("Play"));

    const audio = this.controls.querySelector<HTMLButtonElement>(
      `[data-stx-player-act="${PLAYER_ACTS.audioLanguage}"]`,
    );
    if (audio) {
      audio.textContent = this.activeAudio.toUpperCase();
      audio.dataset.stxPlayerLang = this.activeAudio;
    }
    const captions = this.controls.querySelector<HTMLButtonElement>(
      `[data-stx-player-act="${PLAYER_ACTS.captionLanguage}"]`,
    );
    if (captions) {
      captions.textContent =
        this.activeCaption === "off" ? gettext("CC") : this.activeCaption.toUpperCase();
      captions.setAttribute("aria-pressed", String(this.activeCaption !== "off"));
      captions.dataset.stxPlayerLang = this.activeCaption;
    }
    if (this.chapterRow) {
      const active = this.currentChapterIndex();
      Array.from(this.chapterRow.children).forEach((child, i) => {
        child.setAttribute("aria-current", String(i === active));
      });
    }
  }

  private emit(detail: Omit<TourPlayerChangeDetail, "app"> & { app?: string }): void {
    const full: TourPlayerChangeDetail = { app: this.app, ...detail };
    this.root.dispatchEvent(new CustomEvent(PLAYER_CHANGE, { detail: full, bubbles: true }));
  }
}
