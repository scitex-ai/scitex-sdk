/**
 * VoiceRecorder — MediaRecorder + Web Audio volume visualizer.
 *
 * Ported from scitex-cloud's recorder.ts.
 * Decoupled from Django API URLs — uses SttAdapter callback instead.
 */

/** Adapter for speech-to-text backend. */
export interface SttAdapter {
  transcribe(audioBlob: Blob, model?: string): Promise<string>;
}

export class VoiceRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private analyser: AnalyserNode | null = null;
  private animFrame: number | null = null;
  private stream: MediaStream | null = null;
  private _isRecording = false;

  constructor(
    private readonly volBars: HTMLElement[],
    private readonly micBtn: HTMLButtonElement | null,
  ) {}

  get isRecording(): boolean {
    return this._isRecording;
  }

  async start(
    sttAdapter: SttAdapter,
    onTranscript: (text: string) => void,
    getModel?: () => string,
  ): Promise<void> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      console.error("[STT] Microphone access denied:", err);
      return;
    }

    this.audioChunks = [];
    this.mediaRecorder = new MediaRecorder(this.stream);

    this.mediaRecorder.addEventListener("dataavailable", (e: BlobEvent) => {
      if (e.data.size > 0) this.audioChunks.push(e.data);
    });

    this.mediaRecorder.addEventListener("stop", () => {
      const blob = new Blob(this.audioChunks, { type: "audio/webm" });
      sttAdapter
        .transcribe(blob, getModel?.())
        .then((text) => {
          if (text) onTranscript(text);
        })
        .catch((err) => console.error("[STT] Transcription failed:", err))
        .finally(() => this.micBtn?.classList.remove("transcribing"));
    });

    this.mediaRecorder.start();
    this._isRecording = true;
    this.micBtn?.classList.add("recording");
    this.startVisualizer();
  }

  stop(): void {
    this.mediaRecorder?.stop();
    this._isRecording = false;
    this.micBtn?.classList.remove("recording");
    this.micBtn?.classList.add("transcribing");
    this.stopVisualizer();
  }

  private startVisualizer(): void {
    if (!this.stream) return;
    const ctx = new AudioContext();
    const source = ctx.createMediaStreamSource(this.stream);
    this.analyser = ctx.createAnalyser();
    this.analyser.fftSize = 64;
    source.connect(this.analyser);

    const data = new Uint8Array(this.analyser.frequencyBinCount);
    const bars = this.volBars;
    const n = bars.length;

    const tick = (): void => {
      this.analyser!.getByteFrequencyData(data);
      const step = Math.floor(data.length / n);
      for (let i = 0; i < n; i++) {
        const avg = data[i * step] / 255;
        const scale = Math.max(0.1, avg);
        bars[i].style.transform = `scaleY(${scale})`;
      }
      this.animFrame = requestAnimationFrame(tick);
    };
    this.animFrame = requestAnimationFrame(tick);
    bars.forEach((b) => b.removeAttribute("hidden"));
  }

  private stopVisualizer(): void {
    if (this.animFrame !== null) {
      cancelAnimationFrame(this.animFrame);
      this.animFrame = null;
    }
    this.volBars.forEach((b) => {
      b.style.transform = "scaleY(0.1)";
      b.setAttribute("hidden", "");
    });
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.analyser = null;
  }
}
