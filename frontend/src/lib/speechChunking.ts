const CHUNK_TARGET_LENGTH = 120;
const CHUNK_MAX_LENGTH = 240;
/** Comfortably under the server's per-request MAX_TTS_TEXT_LENGTH (5000,
 * see services/api/app/interface/schemas/speech.py) so every chunk is a
 * small, fast synthesis call instead of one that processes an entire
 * document — this is what makes playback start almost immediately and keeps
 * any single request cheap enough not to stress the speech-service
 * container's resource limits (see docker-compose.yml). */

const SENTENCE_RE = /[^.!?\n]+[.!?]+(?=\s|$)|[^.!?\n]+$/g;

/**
 * Splits text into speech-sized chunks on sentence boundaries, merging
 * short sentences up to ~CHUNK_TARGET_LENGTH so a reader isn't fetching one
 * request per sentence, and hard-splitting the rare sentence that exceeds
 * CHUNK_MAX_LENGTH on its own. Used to feed SpeakButton's chunk-at-a-time
 * playback queue instead of sending a whole document as a single request.
 */
export function chunkTextForSpeech(text: string): string[] {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (!normalized) return [];

  const sentences = normalized.match(SENTENCE_RE) ?? [normalized];
  const chunks: string[] = [];
  let current = "";

  for (const raw of sentences) {
    const sentence = raw.trim();
    if (!sentence) continue;

    if (sentence.length > CHUNK_MAX_LENGTH) {
      if (current) {
        chunks.push(current);
        current = "";
      }
      for (let i = 0; i < sentence.length; i += CHUNK_MAX_LENGTH) {
        chunks.push(sentence.slice(i, i + CHUNK_MAX_LENGTH));
      }
      continue;
    }

    const candidate = current ? `${current} ${sentence}` : sentence;
    if (candidate.length > CHUNK_TARGET_LENGTH && current) {
      chunks.push(current);
      current = sentence;
    } else {
      current = candidate;
    }
  }

  if (current) chunks.push(current);
  return chunks;
}
