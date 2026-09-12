export interface TranslationRun {
  id: number;
  document_id: number | null;
  collection_id: number | null;
  source_lang: string;
  target_lang: string;
  source_text: string;
  translated_text: string;
  word_count: number;
  translated_word_count: number;
  elapsed_ms: number;
  created_at: string;
}

export interface TranslationRunWord {
  rank: number;
  lemma: string;
  surface: string;
  pos: string;
  frequency: number;
  translation: string | null;
}

export interface SyntaxToken {
  position: number;
  text: string;
  lemma: string;
  pos: string;
  dep: string;
  head_position: number | null;
  head_text: string | null;
  morph: Record<string, string>;
  is_punct: boolean;
}

export interface TranslationDictionaryEntry {
  id: number;
  source_lang: string;
  target_lang: string;
  source_lemma: string;
  pos: string | null;
  target_text: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface TranslationDictionaryPage {
  items: TranslationDictionaryEntry[];
  total: number;
}

export interface TranslationDictionaryEntryInput {
  source_lang?: string;
  target_lang?: string;
  source_lemma: string;
  pos?: string | null;
  target_text: string;
  notes?: string | null;
}

export const DEFAULT_SOURCE_LANGUAGE = "en";
export const DEFAULT_TARGET_LANGUAGE = "fr";
