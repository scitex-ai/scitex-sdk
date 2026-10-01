#!/usr/bin/env python3
"""Tour player component metadata."""

from .._registry import register_component


class TourPlayer:
    """Bilingual tour player: audio + subtitle languages, chapters, stable hooks.

    SSOT: scitex-hub PR 923 §8. Two properties are the reason this exists rather
    than a hand-rolled ``<video>`` per app:

    - **Switching a language must not lose the viewer's place.** A JA viewer
      switches language mid-tour, and a switch that silently restarts the video
      reads as losing your place. Position and play state are captured before the
      source swap and restored after it (immediately, and again on
      ``loadedmetadata``, because the seek only sticks once metadata is in).
    - **The recording pipeline locates controls by data attribute, never by
      label.** §8 drives ONE action timeline to produce both the EN and the JA
      recording, so any locator containing prose cannot survive the second
      locale. Every control publishes ``data-stx-player-act``.

    The audio and subtitle choices are independent: a viewer may want JA audio
    with EN subtitles, and setting one must not reset the other.

    TS:  scitex_sdk/ui/ts/app/tour-player/index
    CSS: scitex_sdk/ui/css/app/tour-player.css
    JS:  scitex_sdk/ui/js/app/tour-player.js (pre-built, sets window.stxTourPlayer)
    """

    name = "tour-player"
    version = "0.1.0"
    description = (
        "Bilingual tour video player: audio/subtitle language switching that keeps "
        "position, chapter navigation, and data-attribute hooks the recording "
        "pipeline drives (window.stxTourPlayer)"
    )
    ts_entry = "scitex_sdk/ui/ts/app/tour-player/index"
    css_file = "scitex_sdk/ui/css/app/tour-player.css"
    js_file = "scitex_sdk/ui/js/app/tour-player.js"


register_component(TourPlayer.name, TourPlayer)
