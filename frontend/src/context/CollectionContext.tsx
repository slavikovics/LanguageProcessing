import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { getLatestIndexJob, listCollections } from "../api/client";
import type { Collection, IndexJob } from "../api/types";
import { useIndexJobProgress } from "../hooks/useIndexJobProgress";

const STORAGE_KEY = "ips-selected-collection-id";

interface CollectionContextValue {
  /** Every collection, used to populate the switcher. */
  collections: Collection[];
  /** True only while the initial list is loading. */
  loading: boolean;
  selectedId: number | null;
  /** The full Collection object for `selectedId`, or null. */
  selected: Collection | null;
  setSelectedId: (id: number | null) => void;
  /** Re-fetches the collection list (call after creating/crawling into one). */
  refreshCollections: () => Promise<void>;
  /** Most recent indexing job for the selected collection, if any. */
  latestIndexJob: IndexJob | null;
  /** Re-fetches latestIndexJob (call after starting/finishing an index job). */
  refreshIndexStatus: () => Promise<void>;
  /** Live (polled) "is the selected collection currently being indexed" —
   * shared so any page can disable crawl/refresh/delete actions the backend
   * would reject anyway (see CrawlJobService._ensure_not_indexing). */
  isIndexing: boolean;
}

const CollectionContext = createContext<CollectionContextValue | null>(null);

/**
 * The app is organized around "the collection you're currently working
 * with" — crawling into it, indexing it, searching it, evaluating it. This
 * context is the single source of truth for that selection so every page
 * shares one switcher instead of each re-implementing its own dropdown.
 */
export function CollectionProvider({ children }: { children: ReactNode }) {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedIdState] = useState<number | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? Number(stored) : null;
  });
  const [latestIndexJob, setLatestIndexJob] = useState<IndexJob | null>(null);
  const [activeIndexJobId, setActiveIndexJobId] = useState<number | null>(null);
  const { progress: liveIndexJob } = useIndexJobProgress(activeIndexJobId);

  const setSelectedId = useCallback((id: number | null) => {
    setSelectedIdState(id);
    if (id === null) {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, String(id));
    }
  }, []);

  const refreshCollections = useCallback(async () => {
    setLoading(true);
    try {
      const list = await listCollections();
      setCollections(list);
      setSelectedIdState((prev) => (prev !== null && list.some((c) => c.id === prev) ? prev : (list[0]?.id ?? null)));
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshIndexStatus = useCallback(async () => {
    if (selectedId === null) {
      setLatestIndexJob(null);
      return;
    }
    try {
      setLatestIndexJob(await getLatestIndexJob(selectedId));
    } catch {
      setLatestIndexJob(null);
    }
  }, [selectedId]);

  useEffect(() => {
    void refreshCollections();
  }, [refreshCollections]);

  useEffect(() => {
    void refreshIndexStatus();
  }, [refreshIndexStatus]);

  // Picks up a running job as soon as latestIndexJob reflects it (whether
  // this tab started it or refreshIndexStatus just noticed one already in
  // flight), then subscribes to its live progress so isIndexing stays
  // correct without every page re-implementing this polling.
  useEffect(() => {
    if (latestIndexJob && (latestIndexJob.status === "pending" || latestIndexJob.status === "running")) {
      setActiveIndexJobId(latestIndexJob.id);
    }
  }, [latestIndexJob]);

  useEffect(() => {
    if (liveIndexJob && (liveIndexJob.status === "completed" || liveIndexJob.status === "failed")) {
      setActiveIndexJobId(null);
      void refreshIndexStatus();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [liveIndexJob]);

  const displayedIndexJob = liveIndexJob ?? latestIndexJob;
  const isIndexing =
    displayedIndexJob?.status === "pending" || displayedIndexJob?.status === "running";

  const selected = collections.find((c) => c.id === selectedId) ?? null;

  return (
    <CollectionContext.Provider
      value={{
        collections,
        loading,
        selectedId,
        selected,
        setSelectedId,
        refreshCollections,
        latestIndexJob,
        refreshIndexStatus,
        isIndexing,
      }}
    >
      {children}
    </CollectionContext.Provider>
  );
}

export function useCollectionContext(): CollectionContextValue {
  const ctx = useContext(CollectionContext);
  if (!ctx) {
    throw new Error("useCollectionContext must be used within a CollectionProvider");
  }
  return ctx;
}
