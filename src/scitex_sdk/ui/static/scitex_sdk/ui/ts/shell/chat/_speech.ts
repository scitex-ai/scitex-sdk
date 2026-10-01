/**
 * Text-to-speech utilities for the AI chat panel.
 *
 * Ported from scitex-cloud's speech.ts.
 * Decoupled from Django API URLs — uses TtsAdapter callback instead.
 */

/** Adapter for text-to-speech backend. */
export interface TtsAdapter {
  speak(text: string): Promise<HTMLAudioElement | null>;
}

/** Clean markdown/code from text before speaking. */
export function cleanForSpeech(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, " code block. ")
    .replace(/`[^`]+`/g, "")
    .replace(/\*\*?([^*]+)\*\*?/g, "$1")
    .replace(/#+\s*/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/https?:\/\/\S+/g, " link ")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Speak text — uses TtsAdapter if provided, falls back to browser speechSynthesis.
 */
export async function speakText(
  text: string,
  ttsAdapter?: TtsAdapter,
): Promise<HTMLAudioElement | null> {
  const clean = cleanForSpeech(text);
  if (!clean) return null;

  if (ttsAdapter) {
    try {
      return await ttsAdapter.speak(clean);
    } catch {
      // Fall through to browser TTS
    }
  }

  // Browser built-in TTS fallback
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(clean));
  }
  return null;
}
