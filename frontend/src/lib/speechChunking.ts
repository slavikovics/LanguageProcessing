const CHUNK_TARGET_LENGTH = 120;
// Well under the server's MAX_TTS_TEXT_LENGTH (5000) so playback starts almost immediately.
const CHUNK_MAX_LENGTH = 240;

const SENTENCE_RE = /[^.!?\n]+[.!?]+(?=\s|$)|[^.!?\n]+$/g;

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
