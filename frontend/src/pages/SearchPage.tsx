import {
  HelpCircle,
  ListChecks,
  Loader2,
  SearchIcon,
  SlidersHorizontal,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { clearJudgment, listJudgments, search, setJudgment } from "../api/client";
import type { SearchResponse } from "../api/types";

import { CollectionJudgmentBrowser } from "@/components/CollectionJudgmentBrowser";
import { ResultCard } from "@/components/ResultCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useCollectionContext } from "@/context/CollectionContext";
import { useSearchModelContext } from "@/context/SearchModelContext";
import { clampNumberInput } from "@/lib/utils";

const JUDGMENT_MODE_STORAGE_KEY = "ips-judgment-mode";

export function SearchPage() {
  const { selected, selectedId, latestIndexJob } = useCollectionContext();
  const { models, selectedModelKey, setSelectedModelKey } = useSearchModelContext();
  const [text, setText] = useState("");
  const [topK, setTopK] = useState<number | "">(10);
  const [submittedWords, setSubmittedWords] = useState<string[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [judgments, setJudgments] = useState<Record<number, boolean>>({});
  const [judgmentMode, setJudgmentMode] = useState(
    () => localStorage.getItem(JUDGMENT_MODE_STORAGE_KEY) === "1",
  );
  const [showFullCollection, setShowFullCollection] = useState(false);

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
    setShowFullCollection(false);
    try {
      const result = await search({
        collection_id: selectedId,
        text,
        top_k: clampNumberInput(topK, 1, 100),
        model: selectedModelKey,
      });
      setResponse(result);
      setSubmittedWords(text.trim().split(/\s+/));
      // Queries are deduped by collection+text, so this text may already
      // have prior judgments — hydrate from those instead of starting
      // blank, otherwise previously marked documents would look unjudged.
      try {
        const existing = await listJudgments(result.query_id);
        setJudgments(
          Object.fromEntries(existing.filter((j) => j.is_relevant).map((j) => [j.document_id, true])),
        );
      } catch {
        // Non-critical: results still render, just without pre-filled marks.
      }
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

  // Only "relevant" is a markable state — everything not explicitly marked
  // is treated as not relevant, so a separate "not relevant" mark would add
  // nothing. Clicking again clears the judgment entirely rather than
  // recording a negative, keeping the qrels set to exactly "confirmed relevant".
  async function handleToggleRelevant(documentId: number) {
    if (!response) return;
    const nextRelevant = !judgments[documentId];
    try {
      if (nextRelevant) {
        await setJudgment(response.query_id, documentId, true);
      } else {
        await clearJudgment(response.query_id, documentId);
      }
      setJudgments((prev) => {
        const next = { ...prev };
        if (nextRelevant) next[documentId] = true;
        else delete next[documentId];
        return next;
      });
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
            <Button
              type="button"
              variant={settingsOpen ? "secondary" : "outline"}
              size="icon"
              aria-label="Параметры поиска"
              aria-expanded={settingsOpen}
              onClick={() => setSettingsOpen((v) => !v)}
            >
              <SlidersHorizontal className="size-4" />
            </Button>
            <Button type="submit" size="icon" disabled={loading} aria-label="Искать">
              {loading ? <Loader2 className="size-4 animate-spin" /> : <SearchIcon className="size-4" />}
            </Button>
            <Button asChild variant="outline" size="icon" aria-label="Справка о поиске" className="text-muted-foreground">
              <Link to="/help#searching">
                <HelpCircle className="size-4" />
              </Link>
            </Button>
          </form>

          {settingsOpen && (
            <div className="flex flex-wrap items-end gap-4 rounded-md border bg-muted/30 p-4 duration-150 animate-in fade-in slide-in-from-top-1">
              <div className="flex min-w-52 flex-1 flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="search-model">Модель поиска</Label>
                  <Link
                    to="/help#search-models"
                    aria-label="Подробнее о моделях поиска"
                    className="text-muted-foreground transition-colors hover:text-primary"
                  >
                    <HelpCircle className="size-3.5" />
                  </Link>
                </div>
                <Select value={selectedModelKey} onValueChange={setSelectedModelKey}>
                  <SelectTrigger id="search-model" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {models.map((m) => (
                      <SelectItem key={m.key} value={m.key}>
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex w-56 flex-col gap-1.5">
                <Label htmlFor="search-top-k">Число результатов (Топ-K)</Label>
                <Input
                  id="search-top-k"
                  type="number"
                  min={1}
                  max={100}
                  value={topK}
                  onChange={(e) => setTopK(e.target.value === "" ? "" : Number(e.target.value))}
                  onBlur={() => setTopK((v) => clampNumberInput(v, 1, 100))}
                />
              </div>
            </div>
          )}
        </div>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading && (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
          <Loader2 className="size-6 animate-spin" />
          <p className="text-sm">Идёт поиск…</p>
        </div>
      )}

      {!loading && response && (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              {response.hits.length > 0
                ? `Найдено ${response.hits.length} по запросу «${response.query_text}»`
                : `Совпадений не найдено по запросу «${response.query_text}»`}
              <span className="text-muted-foreground/70"> · модель: {response.model_label}</span>
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
                  isRelevant={judgments[hit.document_id] ?? false}
                  judgmentMode={judgmentMode}
                  submittedWords={submittedWords}
                  onToggleRelevant={handleToggleRelevant}
                />
              ))}
            </div>
          )}

          {judgmentMode && selectedId !== null && selected !== null && (
            <div className="flex flex-col gap-3">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="w-fit self-center"
                onClick={() => setShowFullCollection((v) => !v)}
              >
                <ListChecks className="size-4" />
                {showFullCollection ? "Скрыть остальные документы" : "Проверить остальные документы коллекции"}
              </Button>
              {showFullCollection && (
                <CollectionJudgmentBrowser
                  collectionId={selectedId}
                  documentTotal={selected.document_count}
                  excludeIds={new Set(response.hits.map((hit) => hit.document_id))}
                  judgments={judgments}
                  onToggleRelevant={handleToggleRelevant}
                />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
