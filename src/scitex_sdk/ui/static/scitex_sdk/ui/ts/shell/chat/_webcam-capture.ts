/**
 * WebcamCapture — live camera feed with snapshot for AI chat.
 *
 * Ported from scitex-cloud's webcam-capture.ts.
 * Opens modal overlay with getUserMedia, capture button, camera flip.
 * Falls back to file picker if camera denied.
 *
 * Capture STAGES a photo and leaves the modal open, so several can be taken
 * before Send. Each one lands in the composer immediately, visible behind this
 * overlay and removable by the × on its own thumbnail — which is why closing
 * needs only one button rather than a Cancel/Done pair.
 */

import type { ImageInputManager } from "./_image-input";
import { createHiddenFileInput, MAX_IMAGES } from "./_image-input";

const JPEG_MIME = "image/jpeg";
const JPEG_QUALITY = 0.9;

/**
 * A filename for a photo that never had one.
 *
 * Colons and dots are stripped from the ISO timestamp because a colon is not a
 * legal filename character on Windows, and a stray dot would read as a second
 * extension. The result sorts chronologically as text, which is the property
 * that makes several photos in one message tellable apart later.
 */
export function webcamFilename(now: Date = new Date()): string {
  const stamp = now.toISOString().replace(/\.\d+Z$/, "").replace(/[:]/g, "-");
  return `webcam-${stamp}.jpg`;
}

export class WebcamCapture {
  private overlay: HTMLElement | null = null;
  private video: HTMLVideoElement | null = null;
  private stream: MediaStream | null = null;
  private imageInput: ImageInputManager;
  private fileInput: HTMLInputElement;
  private doneBtn: HTMLButtonElement | null = null;
  private captureBtn: HTMLButtonElement | null = null;
  private hint: HTMLElement | null = null;
  /** Photos staged by THIS session — drives the label, not the global count. */
  private takenHere = 0;

  /**
   * @param fileInput  Used when getUserMedia is refused. Omit it and one is
   *   synthesised carrying `capture="environment"`.
   *
   *   That attribute is the whole point of the fallback: on a phone it opens
   *   the CAMERA, which is what the user asked for by pressing a camera
   *   button. Without it they get a file browser — technically a fallback,
   *   but not to the thing they wanted. A caller-supplied input is used
   *   as-is and never mutated: it is usually the page's general "attach a
   *   file" picker, and forcing `capture` onto it would take away the
   *   ability to choose an existing photo.
   */
  constructor(
    imageInput: ImageInputManager,
    fileInput?: HTMLInputElement | null,
  ) {
    this.imageInput = imageInput;
    if (fileInput) {
      // The manager already listens to the page's own picker; binding here too
      // would add every chosen photo twice.
      this.fileInput = fileInput;
    } else {
      this.fileInput = createHiddenFileInput({ capture: "environment" });
      this.fileInput.addEventListener("change", () => {
        const files = this.fileInput.files;
        if (files) this.imageInput.addFiles(Array.from(files));
        this.fileInput.value = "";
      });
    }
  }

  async open(): Promise<void> {
    if (this.overlay) return;

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 } },
        audio: false,
      });
    } catch {
      this.fileInput.click();
      return;
    }

    this.overlay = this.buildUI();
    document.body.appendChild(this.overlay);
    this.video!.srcObject = this.stream;
  }

  close(): void {
    this.stopStream();
    this.overlay?.remove();
    this.overlay = null;
    this.video = null;
    // Drop the per-session state with the DOM that displayed it. Leaving
    // takenHere set would make the next open() start at "Done (3)" and count
    // photos the user took last time.
    this.doneBtn = null;
    this.captureBtn = null;
    this.hint = null;
    this.takenHere = 0;
  }

  private buildUI(): HTMLElement {
    const overlay = document.createElement("div");
    overlay.className = "stx-shell-webcam-overlay";
    overlay.style.cssText =
      "position:fixed;inset:0;background:rgba(0,0,0,0.8);z-index:10000;display:flex;align-items:center;justify-content:center;";

    const panel = document.createElement("div");
    panel.className = "stx-shell-webcam-panel";
    panel.style.cssText =
      "display:flex;flex-direction:column;align-items:center;gap:12px;padding:16px;background:var(--bg-secondary,#161b22);border-radius:8px;";
    overlay.appendChild(panel);

    this.video = document.createElement("video");
    this.video.autoplay = true;
    this.video.playsInline = true;
    this.video.muted = true;
    this.video.style.cssText =
      "max-width:640px;max-height:480px;border-radius:4px;";
    panel.appendChild(this.video);

    const actions = document.createElement("div");
    actions.style.cssText = "display:flex;gap:12px;";

    // ONE close button, not a Cancel/Done pair. Each capture stages its photo
    // immediately into the composer, where it is visible behind this modal and
    // removable by the × on its own thumbnail — so there is nothing for a
    // "Cancel" to undo that the user cannot already undo. Two buttons that
    // both merely close would be two names for one action. The label carries
    // the state instead.
    this.doneBtn = document.createElement("button");
    this.doneBtn.style.cssText =
      "padding:8px 16px;border-radius:4px;border:1px solid var(--border-default,#30363d);background:none;color:var(--fg-default,#c9d1d9);cursor:pointer;";
    this.doneBtn.addEventListener("click", () => this.close());

    this.captureBtn = document.createElement("button");
    this.captureBtn.innerHTML = '<i class="fas fa-circle"></i> Capture';
    this.captureBtn.style.cssText =
      "padding:8px 16px;border-radius:4px;border:none;background:#ef4444;color:#fff;cursor:pointer;font-size:16px;";
    this.captureBtn.addEventListener("click", () => this.capture());

    this.hint = document.createElement("div");
    this.hint.style.cssText =
      "min-height:1.2em;font-size:13px;color:var(--fg-muted,#8b949e);";

    const flipBtn = document.createElement("button");
    flipBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Flip';
    flipBtn.style.cssText =
      "padding:8px 16px;border-radius:4px;border:1px solid var(--border-default,#30363d);background:none;color:var(--fg-default,#c9d1d9);cursor:pointer;";
    flipBtn.addEventListener("click", () => this.switchCamera());

    actions.append(this.doneBtn, this.captureBtn, flipBtn);
    panel.append(actions, this.hint);
    this.refreshControls();

    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) this.close();
    });

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        this.close();
        document.removeEventListener("keydown", onKey);
      }
    };
    document.addEventListener("keydown", onKey);

    return overlay;
  }

  /**
   * Label and enablement follow the two facts that change: how many photos
   * this session has taken, and whether the composer has room for another.
   *
   * The cap needs saying out loud. `addFile` rejects at MAX_IMAGES without a
   * sound, so before this the Capture button simply stopped working — which
   * reads as a broken button, not a full basket. Now the button goes away and
   * the reason is written next to it.
   */
  private refreshControls(): void {
    const room = this.imageInput.remainingSlots();

    if (this.doneBtn) {
      // "Cancel" while nothing has been staged: closing really is an abort.
      // "Done (N)" once something has: closing is finishing a collection.
      this.doneBtn.textContent =
        this.takenHere === 0 ? "Cancel" : `Done (${this.takenHere})`;
    }
    if (this.captureBtn) {
      this.captureBtn.disabled = room <= 0;
      this.captureBtn.style.opacity = room <= 0 ? "0.5" : "1";
      this.captureBtn.style.cursor = room <= 0 ? "not-allowed" : "pointer";
    }
    if (this.hint) {
      this.hint.textContent =
        room <= 0
          ? `Attachment limit reached (${MAX_IMAGES}). Remove one to take another.`
          : `${room} of ${MAX_IMAGES} slots free — capture as many as you need, then press Done.`;
    }
  }

  private capture(): void {
    if (!this.video) return;
    // Guard as well as disable: Enter can still reach a styled-disabled button
    // in some browsers, and the cap must hold regardless of the UI.
    if (this.imageInput.remainingSlots() <= 0) return;
    const canvas = document.createElement("canvas");
    canvas.width = this.video.videoWidth || 640;
    canvas.height = this.video.videoHeight || 480;
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(this.video, 0, 0, canvas.width, canvas.height);

    // toBlob rather than toDataURL: a data URL is base64, so it carries ~33%
    // more bytes than the image it encodes, and it has nowhere to put a
    // filename. Every photo then reaches the server as an anonymous blob,
    // indistinguishable from every other photo in the same message.
    canvas.toBlob(
      (blob) => {
        if (blob) {
          const file = new File([blob], webcamFilename(), {
            type: JPEG_MIME,
          });
          // Count what was ACCEPTED, not what was offered. A photo rejected at
          // the cap must not inflate "Done (N)" — the label would then promise
          // attachments the composer does not hold.
          this.takenHere += this.imageInput.addFiles([file]);
        } else {
          // toBlob yields null if the canvas cannot be encoded. Keep the photo
          // by the older route rather than closing over a silent loss — the
          // user pressed Capture and is owed an attachment either way.
          const before = this.imageInput.remainingSlots();
          this.imageInput.addImageFromDataUrl(
            canvas.toDataURL(JPEG_MIME, JPEG_QUALITY),
            JPEG_MIME,
          );
          // addImageFromDataUrl reports nothing, so infer acceptance from the
          // slot count rather than assuming it worked.
          if (this.imageInput.remainingSlots() < before) this.takenHere += 1;
        }
        this.refreshControls();
      },
      JPEG_MIME,
      JPEG_QUALITY,
    );
  }

  private async switchCamera(): Promise<void> {
    if (!this.stream || !this.video) return;
    const currentTrack = this.stream.getVideoTracks()[0];
    const currentFacing =
      currentTrack.getSettings().facingMode || "environment";
    const newFacing = currentFacing === "environment" ? "user" : "environment";

    // Flipping is destructive: the old stream must be released before the new
    // one is acquired, because a device with a single camera cannot serve both
    // at once. So a failed acquire leaves us with nothing, and "ignore the
    // error" would strand the modal on a dead preview — stream null, srcObject
    // holding stopped tracks, and the `!this.stream` guard above turning every
    // later Flip into a no-op. On a one-camera desktop that is every Flip.
    this.stopStream();
    if (await this.acquire(newFacing)) return;

    // The new facing is unavailable — the common, boring case. Put back what
    // the user had rather than leaving the session dead.
    if (await this.acquire(currentFacing)) return;

    // Both directions failed: the camera is genuinely gone (unplugged, or
    // claimed by another application). Close instead of presenting a black
    // rectangle that only Cancel can dismiss.
    this.close();
  }

  /** Acquire `facingMode` and attach it. Returns false if unavailable. */
  private async acquire(facingMode: string): Promise<boolean> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode, width: { ideal: 1280 } },
        audio: false,
      });
    } catch {
      this.stream = null;
      return false;
    }
    if (this.video) this.video.srcObject = this.stream;
    return true;
  }

  private stopStream(): void {
    if (this.stream) {
      for (const track of this.stream.getTracks()) track.stop();
      this.stream = null;
    }
  }
}
