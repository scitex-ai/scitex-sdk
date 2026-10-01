/* AUTO-GENERATED from ts/app/tour-player/auto-mount.ts via esbuild — do not edit by hand. Rebuild: npx esbuild ts/app/tour-player/auto-mount.ts --bundle --format=esm --outfile=js/app/tour-player.js */
// ts/_base/gettext.ts
var JS_CATALOG_ELEMENT_PREFIX = "scitex-i18n-catalog-";
var state = null;
function installCatalog(payload) {
  const current = state ?? { entries: {}, plural: null };
  state = {
    entries: { ...current.entries, ...payload.catalog },
    plural: payload.plural ?? current.plural
  };
}
function loadCatalogsFromDocument(doc) {
  const elements = doc.querySelectorAll(
    `script[type="application/json"][id^="${JS_CATALOG_ELEMENT_PREFIX}"]`
  );
  for (const element of Array.from(elements)) {
    installCatalog(JSON.parse(element.textContent || "{}"));
  }
}
function activeCatalog() {
  if (state === null) {
    state = { entries: {}, plural: null };
    if (typeof document !== "undefined") loadCatalogsFromDocument(document);
  }
  return state;
}
function gettext(msgid) {
  const entry = activeCatalog().entries[msgid];
  if (entry === void 0) return msgid;
  const translated = typeof entry === "string" ? entry : entry[0];
  return translated || msgid;
}

// ts/app/tour-player/_TourPlayer.ts
var PLAYER_ATTRIBUTE = "data-stx-tour-player";
var PLAYER_CHANGE = "stx-tour-player:change";
var PLAYER_ACTS = {
  playPause: "play-pause",
  prevChapter: "prev-chapter",
  nextChapter: "next-chapter",
  audioLanguage: "audio-language",
  captionLanguage: "caption-language"
};
var CLS = "stx-tour-player";
var CLS_VIDEO = `${CLS}__video`;
var CLS_CONTROLS = `${CLS}__controls`;
var CLS_CONTROL = `${CLS}__control`;
var CLS_CHAPTERS = `${CLS}__chapters`;
var CLS_CHAPTER = `${CLS}__chapter`;
var TourPlayer = class {
  root;
  app;
  audio;
  subtitles;
  chapterList;
  video;
  controls = null;
  chapterRow = null;
  activeAudio;
  activeCaption;
  /** Set while a source swap is in flight, so the metadata handler can restore. */
  restoringTo = null;
  resumeAfterSwitch = false;
  constructor(root, options) {
    this.root = root;
    this.app = options.app ?? root.getAttribute(PLAYER_ATTRIBUTE) ?? "tour";
    this.audio = options.audio ?? [];
    this.subtitles = options.subtitles ?? [];
    this.chapterList = [...options.chapters ?? []].sort((a, b) => a.start - b.start);
    this.activeAudio = options.audioLanguage ?? this.audio[0]?.lang ?? "en";
    this.activeCaption = options.captionLanguage ?? "off";
    root.classList.add(CLS);
    this.video = document.createElement("video");
    this.video.className = CLS_VIDEO;
    this.video.setAttribute("playsinline", "");
    this.video.preload = "metadata";
    this.video.controls = false;
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
      try {
        this.video.currentTime = target;
      } catch {
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
    this.refreshControls();
    if (options.autoplay) this.play();
  }
  get audioLanguage() {
    return this.activeAudio;
  }
  get captionLanguage() {
    return this.activeCaption;
  }
  get currentTime() {
    return this.video.currentTime;
  }
  set currentTime(seconds) {
    try {
      this.video.currentTime = seconds;
    } catch {
    }
  }
  get chapters() {
    return [...this.chapterList];
  }
  get isPlaying() {
    return !this.video.paused && !this.video.ended;
  }
  /**
   * Switch the audio rendition, keeping the viewer where they were.
   *
   * `wasPlaying` lets a caller that already knows the play state pass it in;
   * otherwise it is read from the element BEFORE the swap, because swapping a
   * source resets `paused` and reading it afterwards would always look stopped.
   */
  setAudioLanguage(lang, options = {}) {
    const track = this.track(this.audio, lang);
    if (!track) return;
    const resumeAt = this.video.currentTime;
    const wasPlaying = options.wasPlaying ?? this.isPlaying;
    this.activeAudio = lang;
    this.restoringTo = resumeAt;
    this.resumeAfterSwitch = wasPlaying;
    this.video.src = track.src;
    this.currentTime = resumeAt;
    this.applyCaptionTracks();
    this.refreshControls();
    if (wasPlaying) this.play();
    this.emit({ change: "audio-language", language: lang, time: resumeAt });
  }
  /** Switch the caption rendition. Captions are a separate track set, so this
   *  never touches the media source and therefore cannot move the position. */
  setCaptionLanguage(lang) {
    const next = lang === "off" || this.track(this.subtitles, lang) ? lang : this.activeCaption;
    this.activeCaption = next;
    this.applyCaptionTracks();
    this.refreshControls();
    this.emit({ change: "caption-language", language: next, time: this.video.currentTime });
  }
  goToChapter(index) {
    const chapter = this.chapterList[index];
    if (!chapter) return;
    this.currentTime = chapter.start;
    this.refreshControls();
    this.emit({ change: "chapter", index, time: chapter.start });
  }
  play() {
    const result = this.video.play();
    if (result && typeof result.catch === "function") result.catch(() => void 0);
    this.refreshControls();
  }
  pause() {
    this.video.pause();
    this.refreshControls();
    this.emit({ change: "pause", time: this.video.currentTime });
  }
  toggle() {
    if (this.isPlaying) this.pause();
    else this.play();
  }
  destroy() {
    this.video.pause();
    this.root.innerHTML = "";
    this.root.classList.remove(CLS);
  }
  track(tracks, lang) {
    return tracks.find((t) => t.lang === lang);
  }
  applyCaptionTracks() {
    const tracks = this.video.textTracks;
    if (!tracks) return;
    for (let i = 0; i < tracks.length; i += 1) {
      const track = tracks[i];
      if (!track) continue;
      const wanted = this.activeCaption !== "off" && track.language === this.activeCaption;
      track.mode = wanted ? "showing" : "disabled";
    }
  }
  renderControls() {
    const row = document.createElement("div");
    row.className = CLS_CONTROLS;
    const make = (act, label, onClick) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `${CLS_CONTROL} ${CLS_CONTROL}--${act}`;
      button.dataset.stxPlayerAct = act;
      button.setAttribute("aria-label", label);
      button.addEventListener("click", onClick);
      return button;
    };
    row.appendChild(
      make(PLAYER_ACTS.playPause, gettext("Play"), () => this.toggle())
    );
    if (this.chapterList.length > 0) {
      row.appendChild(
        make(PLAYER_ACTS.prevChapter, gettext("Previous chapter"), () => this.stepChapter(-1))
      );
      row.appendChild(
        make(PLAYER_ACTS.nextChapter, gettext("Next chapter"), () => this.stepChapter(1))
      );
    }
    if (this.audio.length > 0) {
      row.appendChild(
        make(PLAYER_ACTS.audioLanguage, gettext("Audio language"), () => this.cycleAudio())
      );
    }
    if (this.subtitles.length > 0) {
      row.appendChild(
        make(PLAYER_ACTS.captionLanguage, gettext("Subtitles"), () => this.cycleCaptions())
      );
    }
    return row;
  }
  renderChapters() {
    const row = document.createElement("div");
    row.className = CLS_CHAPTERS;
    row.setAttribute("role", "list");
    this.chapterList.forEach((chapter, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = CLS_CHAPTER;
      button.dataset.stxPlayerChapter = chapter.id ?? String(index);
      button.setAttribute("role", "listitem");
      button.textContent = chapter.title;
      button.addEventListener("click", () => this.goToChapter(index));
      row.appendChild(button);
    });
    return row;
  }
  stepChapter(direction) {
    const next = Math.min(
      Math.max(this.currentChapterIndex() + direction, 0),
      this.chapterList.length - 1
    );
    this.goToChapter(next);
  }
  currentChapterIndex() {
    let index = 0;
    this.chapterList.forEach((chapter, i) => {
      if (this.video.currentTime >= chapter.start) index = i;
    });
    return index;
  }
  cycleAudio() {
    if (this.audio.length === 0) return;
    const current = this.audio.findIndex((t) => t.lang === this.activeAudio);
    const next = this.audio[(current + 1) % this.audio.length];
    if (next) this.setAudioLanguage(next.lang);
  }
  cycleCaptions() {
    const langs = ["off", ...this.subtitles.map((t) => t.lang)];
    const current = langs.indexOf(this.activeCaption);
    this.setCaptionLanguage(langs[(current + 1) % langs.length] ?? "off");
  }
  /** Reflect the state on the controls: labels and `aria-pressed` are the only
   *  things that change, so the hooks stay stable for the pipeline. */
  refreshControls() {
    if (!this.controls) return;
    const play = this.controls.querySelector(
      `[data-stx-player-act="${PLAYER_ACTS.playPause}"]`
    );
    if (play) play.setAttribute("aria-label", this.isPlaying ? gettext("Pause") : gettext("Play"));
    const audio = this.controls.querySelector(
      `[data-stx-player-act="${PLAYER_ACTS.audioLanguage}"]`
    );
    if (audio) {
      audio.textContent = this.activeAudio.toUpperCase();
      audio.dataset.stxPlayerLang = this.activeAudio;
    }
    const captions = this.controls.querySelector(
      `[data-stx-player-act="${PLAYER_ACTS.captionLanguage}"]`
    );
    if (captions) {
      captions.textContent = this.activeCaption === "off" ? gettext("CC") : this.activeCaption.toUpperCase();
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
  emit(detail) {
    const full = { app: this.app, ...detail };
    this.root.dispatchEvent(new CustomEvent(PLAYER_CHANGE, { detail: full, bubbles: true }));
  }
};

// ts/app/tour-player/auto-mount.ts
var SCRIPT_ID_PREFIX = "stx-tour-player-";
function loadPlayerOptions(app, doc = document) {
  const script = doc.getElementById(`${SCRIPT_ID_PREFIX}${app}`);
  if (!script?.textContent) return null;
  try {
    return JSON.parse(script.textContent);
  } catch {
    return null;
  }
}
function mountTourPlayers(doc = document) {
  const mounted = [];
  doc.querySelectorAll(`[${PLAYER_ATTRIBUTE}]`).forEach((root) => {
    if (root.querySelector(".stx-tour-player__video")) return;
    const app = root.getAttribute(PLAYER_ATTRIBUTE) ?? "tour";
    const options = loadPlayerOptions(app, doc);
    if (!options) return;
    mounted.push(new TourPlayer(root, { ...options, app }));
  });
  return mounted;
}
var stxTourPlayer = { TourPlayer, mountTourPlayers, loadPlayerOptions };
if (typeof window !== "undefined") {
  window.stxTourPlayer = stxTourPlayer;
  const autoMount = () => {
    mountTourPlayers();
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoMount);
  } else {
    autoMount();
  }
}
export {
  PLAYER_ACTS,
  PLAYER_ATTRIBUTE,
  PLAYER_CHANGE,
  SCRIPT_ID_PREFIX,
  TourPlayer,
  loadPlayerOptions,
  mountTourPlayers,
  stxTourPlayer
};
