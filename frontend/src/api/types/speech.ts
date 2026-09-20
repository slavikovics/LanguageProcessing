export interface SpeechVoiceOption {
  value: string;
  label: string;
}

export const TTS_VOICES: SpeechVoiceOption[] = [
  { value: "en_US-amy-medium", label: "Amy (US, женский)" },
  { value: "en_US-lessac-medium", label: "Lessac (US, женский)" },
  { value: "en_US-hfc_female-medium", label: "HFC Female (US, женский)" },
  { value: "en_US-kristin-medium", label: "Kristin (US, женский)" },
  { value: "en_US-ryan-medium", label: "Ryan (US, мужской)" },
  { value: "en_US-hfc_male-medium", label: "HFC Male (US, мужской)" },
  { value: "en_US-joe-medium", label: "Joe (US, мужской)" },
  { value: "en_GB-alba-medium", label: "Alba (UK, женский)" },
  { value: "en_GB-jenny_dioco-medium", label: "Jenny (UK, женский)" },
  { value: "en_GB-alan-medium", label: "Alan (UK, мужской)" },
];

export interface SpeechCommand {
  id: number;
  phrase: string;
  action: string;
  language: string;
  is_active: boolean;
  created_at: string;
}
