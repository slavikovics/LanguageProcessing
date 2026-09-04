import { ChevronDown, Globe, SearchIcon, SlidersHorizontal, ThumbsDown, ThumbsUp } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { getDocument, search, setJudgment } from "../api/client";
import type { SearchHit, SearchResponse } from "../api/types";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Switch } from "@/components/ui/switch";
import { useCollectionContext } from "@/context/CollectionContext";
import { cn } from "@/lib/utils";

const JUDGMENT_MODE_STORAGE_KEY = "ips-judgment-mode";

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlightSnippet(snippet: string, words: string[]): ReactNode {
  const cleaned = [...new Set(words.filter(Boolean))];
  if (cleaned.length === 0) return snippet;
  const pattern = new RegExp(`(${cleaned.map(escapeRegExp).join("|")})`, "gi");
  const parts = snippet.split(pattern);
  return parts.map((part, i) =>
    cleaned.some((w) => w.toLowerCase() === part.toLowerCase()) ? (
      <mark key={i} className="rounded bg-yellow-200 px-0.5 text-foreground dark:bg-yellow-900/60">
        {part}
      </mark>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

type JudgmentState = "relevant" | "not_relevant" | null;

function ResultCard({
  hit,
  judgment,
  judgmentMode,
  submittedWords,
  onJudge,
}: {
  hit: SearchHit;
  judgment: JudgmentState;
  judgmentMode: boolean;
  submittedWords: string[];
  onJudge: (hit: SearchHit, isRelevant: boolean) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [fullText, setFullText] = useState<string | null>(null);
  const [loadingFull, setLoadingFull] = useState(false);

  async function toggleExpand() {
    if (expanded) {
      setExpanded(false);
      return;
    }
    setExpanded(true);
    if (fullText === null) {
      setLoadingFull(true);
      try {
        const detail = await getDocument(hit.document_id);
        setFullText(detail.clean_text);
      } catch {
        setFullText(hit.snippet);
      } finally {
        setLoadingFull(false);
      }
    }
  }

  return (
    <div className="flex flex-col gap-2.5 rounded-md border p-4 transition-shadow duration-200 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-baseline gap-2">
          <span className="shrink-0 text-sm font-semibold text-muted-foreground">#{hit.rank}</span>
          <span className="min-w-0 truncate font-medium">{hit.title}</span>
        </div>
        <div className="shrink-0 text-right text-xs text-muted-foreground">
          <div>score {hit.score.toFixed(3)}</div>
          <div>{new Date(hit.fetched_at).toLocaleDateString()}</div>
        </div>
      </div>

      {!expanded ? (
        <p className="text-sm leading-relaxed text-muted-foreground">
          {highlightSnippet(hit.snippet, submittedWords)}
        </p>
      ) : (
        <div className="flex flex-col gap-2 duration-200 animate-in fade-in slide-in-from-top-1">
          <ScrollArea className="h-56 rounded-md border bg-muted/20">
            <p className="whitespace-pre-wrap p-3 text-sm leading-relaxed">
              {loadingFull ? "Загрузка…" : highlightSnippet(fullText ?? hit.snippet, submittedWords)}
            </p>
          </ScrollArea>
          {hit.matched_terms.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {hit.matched_terms.map((term) => (
                <Badge key={term} variant="outline">
                  {term}
                </Badge>
              ))}
            </div>
          )}
        </div>
      )}

      <button
        type="button"
        onClick={toggleExpand}
        className="flex w-fit items-center gap-1 text-xs text-primary transition-colors hover:text-primary/70"
      >
        <ChevronDown className={cn("size-3.5 transition-transform duration-200", expanded && "rotate-180")} />
        {expanded ? "Свернуть" : "Показать полностью"}
      </button>

      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
          {hit.url ? (
            <>
              <Globe className="size-3.5 shrink-0" />
              <a
                href={hit.url}
                target="_blank"
                rel="noreferrer"
                className="min-w-0 truncate transition-colors hover:text-primary hover:underline"
              >
                {hit.url}
              </a>
            </>
          ) : (
            <span className="italic text-muted-foreground/70">без источника</span>
          )}
        </div>
        {judgmentMode && (
          <div className="flex shrink-0 items-center gap-1">
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={() => onJudge(hit, true)}
              aria-label="Релевантен"
              aria-pressed={judgment === "relevant"}
              className={cn(
                "transition-all duration-150 hover:scale-110",
                judgment === "relevant" && "bg-emerald-600/15 text-emerald-600 dark:text-emerald-400",
              )}
            >
              <ThumbsUp className="size-4" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={() => onJudge(hit, false)}
              aria-label="Не релевантен"
              aria-pressed={judgment === "not_relevant"}
              className={cn(
                "transition-all duration-150 hover:scale-110",
                judgment === "not_relevant" && "bg-destructive/15 text-destructive",
              )}
            >
              <ThumbsDown className="size-4" />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export function SearchPage() {
  const { selected, selectedId, latestIndexJob } = useCollectionContext();
  const [text, setText] = useState("");
  const [topK, setTopK] = useState(10);
  const [submittedWords, setSubmittedWords] = useState<string[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [judgments, setJudgments] = useState<Record<number, JudgmentState>>({});
  const [judgmentMode, setJudgmentMode] = useState(
    () => localStorage.getItem(JUDGMENT_MODE_STORAGE_KEY) === "1",
  );

  const isIndexed = latestIndexJob?.status === "completed";
  const isStale =
    isIndexed &&
    latestIndexJob?.finished_at != null &&
    selected?.documents_changed_at != null &&
    new Date(selected.documents_changed_at) > new Date(latestIndexJob.finished_at);

  function toggleJudgmentMode(enabled: boolean) {
    setJudgmentMode(enabled);
    localStorage.setItem(JUDGMENT_MODE_STORAGE_KEY, enabled ? "1" : "0");
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (selectedId === null) {
      setError("Выберите коллекцию вверху страницы.");
      return;
    }
    if (!text.trim()) {
      setError("Введите текст запроса.");
      return;
    }

    setLoading(true);
    setJudgments({});
    try {
      const result = await search({ collection_id: selectedId, text, top_k: topK });
      setResponse(result);
      setSubmittedWords(text.trim().split(/\s+/));
    } catch (err) {
      setResponse(null);
      const message = err instanceof Error ? err.message : String(err);
      setError(
        message.includes("422")
          ? "Ничего не найдено — возможно, коллекция ещё не проиндексирована."
          : message,
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleJudgment(hit: SearchHit, isRelevant: boolean) {
    if (!response) return;
    try {
      await setJudgment(response.query_id, hit.document_id, isRelevant);
      setJudgments((prev) => ({
        ...prev,
        [hit.document_id]: isRelevant ? "relevant" : "not_relevant",
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {selectedId === null ? (
        <p className="text-sm text-muted-foreground">
          Выберите коллекцию вверху страницы, или создайте новую через «+».
        </p>
      ) : !isIndexed ? (
        <div className="flex items-center justify-between gap-4 rounded-md border border-amber-600/30 bg-amber-600/5 px-3 py-2 text-sm dark:border-amber-400/30">
          <span>
            Коллекция «{selected?.name}» ещё не проиндексирована — поиск не найдёт документы, пока
            не построен индекс.
          </span>
          <Button asChild size="sm" variant="secondary" className="shrink-0">
            <Link to="/collections">Проиндексировать</Link>
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {isStale && (
            <div className="flex items-center justify-between gap-4 rounded-md border border-amber-600/30 bg-amber-600/5 px-3 py-2 text-sm dark:border-amber-400/30">
              <span>
                Документы менялись после последней индексации — результаты поиска могут не
                учитывать последние изменения.
              </span>
              <Button asChild size="sm" variant="secondary" className="shrink-0">
                <Link to="/collections">Переиндексировать</Link>
              </Button>
            </div>
          )}
          <form onSubmit={handleSubmit} className="flex items-center gap-2">
            <div className="relative min-w-0 flex-1">
              <SearchIcon className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                type="text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Запрос на английском, например machine learning applications"
                className="pl-9"
              />
            </div>
            <Popover>
              <PopoverTrigger asChild>
                <Button type="button" variant="outline" size="icon" aria-label="Параметры поиска">
                  <SlidersHorizontal className="size-4" />
                </Button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-64">
                <div className="grid gap-1.5">
                  <Label htmlFor="search-top-k">Число результатов (Топ-K)</Label>
                  <Input
                    id="search-top-k"
                    type="number"
                    min={1}
                    max={100}
                    value={topK}
                    onChange={(e) => setTopK(Number(e.target.value))}
                  />
                </div>
              </PopoverContent>
            </Popover>
            <Button type="submit" size="icon" disabled={loading} aria-label="Искать">
              <SearchIcon className="size-4" />
            </Button>
          </form>
        </div>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}

      {response && (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              {response.hits.length > 0
                ? `Найдено ${response.hits.length} по запросу «${response.query_text}»`
                : `Совпадений не найдено по запросу «${response.query_text}»`}
            </p>
            <label className="flex shrink-0 items-center gap-2 text-sm">
              <span className="text-muted-foreground">Режим разметки</span>
              <Switch checked={judgmentMode} onCheckedChange={toggleJudgmentMode} />
            </label>
          </div>
          {response.hits.length > 0 && (
            <div className="flex flex-col gap-4">
              {response.hits.map((hit) => (
                <ResultCard
                  key={hit.document_id}
                  hit={hit}
                  judgment={judgments[hit.document_id] ?? null}
                  judgmentMode={judgmentMode}
                  submittedWords={submittedWords}
                  onJudge={handleJudgment}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
