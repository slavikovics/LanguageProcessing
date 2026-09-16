export interface SpeechActionInfo {
  label: string;
  hint: string;
}

export const ACTION_LABELS: Record<string, SpeechActionInfo> = {
  navigate_search: {
    label: "Перейти к поиску",
    hint: "Открывает поиск и подставляет сказанное как поисковый запрос",
  },
  clear_query: {
    label: "Очистить запрос",
    hint: "Очищает поле поискового запроса",
  },
  read_document: {
    label: "Прочитать документ",
    hint: "Озвучивает открытый документ или первый найденный на странице блок с возможностью воспроизведения (реферат, перевод)",
  },
  stop_speaking: {
    label: "Остановить озвучивание",
    hint: "Останавливает текущее чтение вслух",
  },
  navigate_to_crawl: {
    label: "Перейти к кроулингу",
    hint: "Открывает вкладку «Кроулинг»",
  },
  navigate_to_collections: {
    label: "Перейти к коллекциям",
    hint: "Открывает вкладку «Коллекции»",
  },
  navigate_to_search: {
    label: "Перейти к поиску (без запроса)",
    hint: "Открывает вкладку «Поиск», не подставляя запрос",
  },
  navigate_to_metrics: {
    label: "Перейти к метрикам",
    hint: "Открывает вкладку «Метрики»",
  },
  navigate_to_lang_id: {
    label: "Перейти к определению языка",
    hint: "Открывает вкладку «Язык»",
  },
  navigate_to_summarization: {
    label: "Перейти к реферированию",
    hint: "Открывает вкладку «Реферирование»",
  },
  navigate_to_translation: {
    label: "Перейти к переводу",
    hint: "Открывает вкладку «Перевод»",
  },
  navigate_to_settings: {
    label: "Перейти к настройкам",
    hint: "Открывает вкладку «Настройки»",
  },
  navigate_to_help: {
    label: "Перейти к справке",
    hint: "Открывает вкладку «Справка»",
  },
};

export function describeAction(action: string): SpeechActionInfo {
  return ACTION_LABELS[action] ?? { label: action, hint: "Пользовательское действие" };
}
