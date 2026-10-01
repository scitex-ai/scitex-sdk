/**
 * Attachment chips — public types.
 */

export interface ImageAttachmentConfig {
  /** Where the anchor points. Presentation only — base owns no storage path. */
  href: string;
  /** Image source. Often the same as `href`; kept separate for thumbnails. */
  src?: string;
  /** Alt text. Required rather than optional: an unlabelled image is a gap. */
  alt: string;
}

export interface FileAttachmentConfig {
  href: string;
  /** Filename shown in the chip. */
  name: string;
  /**
   * Leading mark. Defaults to the literal "📎 " text prefix scitex-cards
   * shipped, preserving their markup contract exactly.
   *
   * Pass an icon-font class instead (e.g. "fas fa-paperclip") to render an
   * `<i>` slot. That is a DIFFERENT markup contract — offered, never imposed.
   *
   * DO NOT MAKE THE ICON THE DEFAULT. scitex-cards' reason, which is about a
   * failure mode rather than taste: their chat is read on phone Safari over a
   * tunnel, in a Telegram-replacement role. An `<i>` slot needs a font that
   * RESOLVED, and when it does not the user gets an empty box where the file
   * affordance was. A text 📎 degrades to a 📎. They are not a consumer of
   * this option and asked that it stay opt-in permanently.
   */
  iconClass?: string;
}
