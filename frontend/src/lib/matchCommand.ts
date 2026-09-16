/** Mirrors match_command in services/api/app/domain/speech.py so global
 * speech mode can react to commands client-side (no network round-trip per
 * utterance) using the exact same "normalize, then substring-contains"
 * rule the backend already applies after a recording is transcribed. */

const PUNCT_RE = /[^\p{L}\p{N}_\s]/gu;
const WHITESPACE_RE = /\s+/g;

function normalize(text: string): string {
  return text.replace(PUNCT_RE, " ").replace(WHITESPACE_RE, " ").toLowerCase().trim();
}

export interface MatchableCommand {
  phrase: string;
  is_active: boolean;
}

export function matchCommand<T extends MatchableCommand>(
  transcript: string,
  commands: T[],
): T | null {
  const normalized = normalize(transcript);
  if (!normalized) return null;
  for (const command of commands) {
    if (!command.is_active) continue;
    if (normalized.includes(normalize(command.phrase))) return command;
  }
  return null;
}
