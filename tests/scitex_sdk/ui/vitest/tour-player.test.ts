/**
 * Tour player: language switching that does not lose the viewer's place.
 *
 * SSOT: scitex-hub PR 923 §8 — "The player can switch audio/subtitle language
 * without losing position", "Stable IDs/data attributes, not translated labels,
 * locate controls" (that one is the recording pipeline's whole footing), and
 * "Record both EN and JA UI locales from the same action timeline".
 *
 * WHY THIS TEST EXISTS IN THIS SHAPE. The expensive failure of a bilingual
 * player is not that a language is missing; it is that switching one SILENTLY
 * restarts the video, which a user experiences as losing their place — and the
 * second language is exactly what a JA researcher switches to mid-tour. So the
 * assertions below are about POSITION and about the two language choices staying
 * independent, not about labels.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { TourPlayer } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/tour-player";
import type { TourPlayerOptions } from "../../../../src/scitex_sdk/ui/static/scitex_sdk/ui/ts/app/tour-player";

const OPTIONS: TourPlayerOptions = {
  app: "demo",
  audio: [
    { lang: "en", src: "/media/tour-en.mp4" },
    { lang: "ja", src: "/media/tour-ja.mp4" },
  ],
  subtitles: [
    { lang: "en", src: "/media/tour-en.vtt", label: "English" },
    { lang: "ja", src: "/media/tour-ja.vtt", label: "日本語" },
  ],
  chapters: [
    { title: "Create a project", start: 0 },
    { title: "Find literature", start: 42 },
    { title: "Compile the paper", start: 96.5 },
  ],
};

function mount(extra: Partial<TourPlayerOptions> = {}): TourPlayer {
  const root = document.createElement("div");
  root.setAttribute("data-stx-tour-player", "demo");
  document.body.appendChild(root);
  return new TourPlayer(root, { ...OPTIONS, ...extra });
}

beforeEach(() => {
  document.body.innerHTML = "";
});

describe("language switching keeps the viewer's place", () => {
  it("keeps currentTime when the caption language changes", () => {
    const player = mount();
    player.currentTime = 12.5;
    player.setCaptionLanguage("ja");
    expect(player.currentTime).toBe(12.5);
  });

  it("keeps currentTime when the audio language changes", () => {
    const player = mount();
    player.currentTime = 12.5;
    player.setAudioLanguage("ja");
    expect(player.currentTime).toBe(12.5);
  });

  it("keeps the two language choices independent", () => {
    const player = mount();
    player.setCaptionLanguage("ja");
    player.setAudioLanguage("ja");
    player.setAudioLanguage("en");
    expect(player.captionLanguage).toBe("ja");
  });

  it("resumes playback after a switch when it was playing before it", () => {
    const player = mount();
    player.currentTime = 30;
    const media = document.querySelector("video") as HTMLVideoElement;
    const play = vi.spyOn(media, "play").mockResolvedValue(undefined);
    player.setAudioLanguage("ja", { wasPlaying: true });
    expect(play).toHaveBeenCalled();
  });

  it("starts on the first audio track with captions OFF", () => {
    // Captions off is the contract, not an omission: a player that starts
    // captioned has made a choice the viewer did not, and the viewer who needs
    // them will turn them on — the same reason the tour itself is an offer.
    const player = mount();
    expect([player.audioLanguage, player.captionLanguage]).toEqual(["en", "off"]);
  });
});

describe("chapters", () => {
  it("exposes the declared chapters in order", () => {
    const player = mount();
    expect(player.chapters.map((c) => c.title)).toEqual([
      "Create a project",
      "Find literature",
      "Compile the paper",
    ]);
  });

  it("seeks to a chapter's start", () => {
    const player = mount();
    player.goToChapter(2);
    expect(player.currentTime).toBe(96.5);
  });
});

describe("stable hooks (the recording pipeline targets these, not labels)", () => {
  it("marks every control with a data-stx-player-act hook", () => {
    mount();
    const acts = Array.from(document.querySelectorAll("[data-stx-player-act]")).map((n) =>
      n.getAttribute("data-stx-player-act"),
    );
    expect(acts.sort()).toEqual([
      "audio-language",
      "caption-language",
      "next-chapter",
      "play-pause",
      "prev-chapter",
    ]);
  });

  it("does not autoplay on mount", () => {
    const player = mount();
    expect(player.isPlaying).toBe(false);
  });
});
