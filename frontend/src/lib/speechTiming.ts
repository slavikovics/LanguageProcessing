export const PHRASE_PAUSE_MS = 1800;
export const MESSAGE_HOLD_MS = PHRASE_PAUSE_MS * 3;

// Mic level (0..1) above which the user counts as speaking.
export const SILENCE_LEVEL_THRESHOLD = 0.06;
export const UTTERANCE_SILENCE_GAP_MS = PHRASE_PAUSE_MS;
export const MAX_UTTERANCE_MS = 12000;
// Chrome's recognizer may still be finalizing speech tail; wait for caption stream to settle too.
export const CAPTION_SETTLE_MS = 500;
// Gateway keeps the socket open on backend failure; treat N consecutive chunk errors as dead.
export const REPEATED_ERROR_LIMIT = 3;
