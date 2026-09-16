// Mirrors match_command in services/api/app/domain/speech.py for client-side matching.
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
