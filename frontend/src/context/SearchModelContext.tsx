import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { listSearchModels } from "../api/client";
import type { SearchModel } from "../api/types";

const STORAGE_KEY = "ips-selected-search-model";
const DEFAULT_MODEL_KEY = "tfidf";

interface SearchModelContextValue {
  /** Every active registered search model — populates the Search page's
   * model picker and the Metrics page's comparison checklist. */
  models: SearchModel[];
  loading: boolean;
  /** The model the Search page currently searches with. */
  selectedModelKey: string;
  setSelectedModelKey: (key: string) => void;
  /** Re-fetches the model list. */
  refreshModels: () => Promise<void>;
}

const SearchModelContext = createContext<SearchModelContextValue | null>(null);

/**
 * Mirrors CollectionContext's pattern for "the thing you're currently
 * working with" — here, which search model the Search page uses. New
 * models show up automatically once the backend registers them (GET
 * /search-models), no frontend code change needed to list them.
 */
export function SearchModelProvider({ children }: { children: ReactNode }) {
  const [models, setModels] = useState<SearchModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedModelKey, setSelectedModelKeyState] = useState<string>(() => {
    return localStorage.getItem(STORAGE_KEY) ?? DEFAULT_MODEL_KEY;
  });

  const setSelectedModelKey = useCallback((key: string) => {
    setSelectedModelKeyState(key);
    localStorage.setItem(STORAGE_KEY, key);
  }, []);

  const refreshModels = useCallback(async () => {
    setLoading(true);
    try {
      const list = await listSearchModels();
      setModels(list);
      setSelectedModelKeyState((prev) =>
        list.some((m) => m.key === prev) ? prev : (list[0]?.key ?? DEFAULT_MODEL_KEY),
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshModels();
  }, [refreshModels]);

  return (
    <SearchModelContext.Provider
      value={{ models, loading, selectedModelKey, setSelectedModelKey, refreshModels }}
    >
      {children}
    </SearchModelContext.Provider>
  );
}

export function useSearchModelContext(): SearchModelContextValue {
  const ctx = useContext(SearchModelContext);
  if (!ctx) {
    throw new Error("useSearchModelContext must be used within a SearchModelProvider");
  }
  return ctx;
}
