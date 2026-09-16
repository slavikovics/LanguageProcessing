/**
 * Shared speech-turn timing, kept in one place so the pause-detection wait
 * (how long you can go quiet before the app decides you've finished
 * talking) and how long the resulting on-screen messages stay visible move
 * together instead of drifting out of sync across the ambient assistant
 * (SpeechModeContext) and push-to-talk dictation (VoiceInputButton).
 */

/** How long a pause in speech must last before a phrase is considered
 * finished — used both to auto-stop push-to-talk dictation and to decide
 * when to check an ambient-mode utterance against active commands. */
export const PHRASE_PAUSE_MS = 1800;

/** How long a one-off confirmation/status message (e.g. "voice mode: «X»")
 * stays on screen before it's dismissed on its own — a multiple of
 * PHRASE_PAUSE_MS so a longer pause-detection wait also means more time to
 * actually read the message that follows it. */
export const MESSAGE_HOLD_MS = PHRASE_PAUSE_MS * 3;
