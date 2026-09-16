export interface SpeechVoiceOption {
  value: string;
  label: string;
}

export const TTS_VOICES: SpeechVoiceOption[] = [
  { value: "en_US-amy-medium", label: "Amy (женский)" },
  { value: "en_US-ryan-medium", label: "Ryan (мужской)" },
];

export interface SpeechCommand {
  id: number;
  phrase: string;
  action: string;
  language: string;
  is_active: boolean;
  created_at: string;
}
