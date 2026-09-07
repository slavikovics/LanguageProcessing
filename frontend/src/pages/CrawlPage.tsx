import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  cancelCrawlJob,
  createCrawlSeed,
  deleteCrawlSeed,
  listCrawlJobs,
  listCrawlSeeds,
  runCollectionCrawl,
  updateCrawlSeed,
} from "../api/client";
import { ProgressBar } from "../components/ProgressBar";
import { useCrawlJobProgress } from "../hooks/useCrawlJobProgress";
import { TERMINAL_CRAWL_STATUSES, type CrawlJob, type CrawlSeed } from "../api/types";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useCollectionContext } from "@/context/CollectionContext";
import { clampNumberInput, cn } from "@/lib/utils";
import {
  Check,
  FileStack,
  Globe,
  HelpCircle,
  Layers,
  Link2,
  Lock,
  Pencil,
  Play,
  Plus,
  Square,
  Waypoints,
  X,
} from "lucide-react";

const QUICK_LANGUAGES = ["en", "fr"];
const DEFAULT_LANGUAGE = "en";

const STATUS_LABELS: Record<CrawlJob["status"], string> = {
  pending: "в очереди",
  running: "выполняется",
  completed: "завершён",
  failed: "ошибка",
  cancelled: "отменён",
};

const STATUS_BADGE_CLASS: Record<CrawlJob["status"], string> = {
  pending: "border-primary/40 text-primary",
  running: "border-primary/40 text-primary",
  completed: "border-emerald-600/40 text-emerald-600 dark:border-emerald-400/40 dark:text-emerald-400",
  failed: "border-destructive/40 text-destructive",
  cancelled: "border-destructive/40 text-destructive",
};

const URL_STATUS_COLOR: Record<string, string> = {
  success: "text-emerald-600 dark:text-emerald-400",
  failed: "text-destructive",
  skipped: "text-destructive",
};

const DEFAULT_MAX_DOCUMENTS = 20;
const DEFAULT_MAX_DEPTH = 1;

function CrawlJobProgressCard({ jobId }: { jobId: number }) {
  const { refreshCollections } = useCollectionContext();
  const { progress } = useCrawlJobProgress(jobId);
  const [cancelling, setCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  // The document count shown in the header switcher is fetched once on
  // load; without this the "Индексировать" button on Collections stays
  // disabled (0 documents) until a manual page reload.
  useEffect(() => {
    if (progress?.job.status === "completed") {
      void refreshCollections();
    }
  }, [progress?.job.status, refreshCollections]);

  if (!progress) return null;

  const isActive = progress.job.status === "pending" || progress.job.status === "running";

  async function handleCancel() {
    setCancelling(true);
    setCancelError(null);
    try {
      await cancelCrawlJob(jobId);
    } catch (err) {
      setCancelError(err instanceof Error ? err.message : String(err));
    } finally {
      setCancelling(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <CardTitle className="flex items-center gap-2">
            <span>Задача #{progress.job.id}</span>
            <Badge variant="outline" className={STATUS_BADGE_CLASS[progress.job.status]}>
              {STATUS_LABELS[progress.job.status]}
            </Badge>
          </CardTitle>
          <div className="flex shrink-0 items-center gap-3">
            <p className="text-right text-xs text-muted-foreground">
              Посещено: {progress.job.urls_visited} · В очереди: {progress.job.urls_queued} · Ошибок:{" "}
              {progress.job.urls_failed}
            </p>
            {isActive && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleCancel}
                disabled={cancelling}
                className="text-destructive hover:bg-destructive/10 hover:text-destructive"
              >
                <Square className="size-3.5" />
                {cancelling ? "Прерывание…" : "Прервать"}
              </Button>
            )}
          </div>
        </div>
        {cancelError && <p className="text-sm text-destructive">{cancelError}</p>}
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <span className="max-w-full truncate text-xs text-muted-foreground" title={progress.job.seed_urls[0]}>
          {progress.job.seed_urls[0]}
        </span>

        <ProgressBar
          value={progress.job.documents_fetched}
          max={progress.job.max_documents}
          complete={TERMINAL_CRAWL_STATUSES.includes(progress.job.status)}
        />

        {progress.job.error_message && (
          <p className="text-sm text-destructive">{progress.job.error_message}</p>
        )}

        {progress.job.status === "completed" && (
          <div className="flex items-center gap-2 rounded-md border border-emerald-600/30 bg-emerald-600/5 px-3 py-2 text-sm dark:border-emerald-400/30">
            <span>Готово: {progress.job.documents_fetched} документов сохранено.</span>
            <Button asChild size="sm" variant="secondary" className="ml-auto shrink-0">
              <Link to="/collections">К индексации</Link>
            </Button>
          </div>
        )}

        <div>
          <h3 className="mb-2 text-xs font-medium text-muted-foreground">Последние URL</h3>
          <ScrollArea className="h-56 rounded-md border">
            <ul className="flex flex-col gap-0.5 p-2">
              {progress.recent_urls.map((u) => (
                <li
                  key={u.id}
                  className="flex items-baseline gap-2 rounded px-2 py-1 text-xs transition-colors duration-150 hover:bg-muted"
                >
                  <span className={cn("shrink-0 font-semibold uppercase", URL_STATUS_COLOR[u.status])}>
                    {u.status}
                  </span>
                  <span className="shrink-0 text-muted-foreground">d{u.depth}</span>
                  <span className="min-w-0 flex-1 truncate" title={u.url}>
                    {u.url}
                  </span>
                  {u.error && (
                    <span className="max-w-[35%] shrink-0 truncate text-destructive" title={u.error}>
                      {u.error}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </ScrollArea>
        </div>
      </CardContent>
    </Card>
  );
}

export function CrawlPage() {
  const { selected, selectedId, isIndexing } = useCollectionContext();

  const [seeds, setSeeds] = useState<CrawlSeed[]>([]);
  const [seedsLoading, setSeedsLoading] = useState(false);

  const [urlDraft, setUrlDraft] = useState("");
  const [maxDocuments, setMaxDocuments] = useState<number | "">(DEFAULT_MAX_DOCUMENTS);
  const [maxDepth, setMaxDepth] = useState<number | "">(DEFAULT_MAX_DEPTH);
  const [sameDomainOnly, setSameDomainOnly] = useState(false);
  const [language, setLanguage] = useState(DEFAULT_LANGUAGE);
  const [editingSeedId, setEditingSeedId] = useState<number | null>(null);
  const [savingSeed, setSavingSeed] = useState(false);
  const [deletingSeedId, setDeletingSeedId] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [latestJobBySeedUrl, setLatestJobBySeedUrl] = useState<Map<string, CrawlJob>>(new Map());

  const refreshSeeds = useCallback(async () => {
    if (selectedId === null) {
      setSeeds([]);
      return;
    }
    setSeedsLoading(true);
    try {
      setSeeds(await listCrawlSeeds(selectedId));
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setSeedsLoading(false);
    }
  }, [selectedId]);

  const refreshSeedJobs = useCallback(async () => {
    if (selectedId === null) {
      setLatestJobBySeedUrl(new Map());
      return;
    }
    try {
      const jobs = await listCrawlJobs(selectedId);
      const latest = new Map<string, CrawlJob>();
      // Jobs come back newest-first, so the first job seen per seed URL is its latest run.
      for (const job of jobs) {
        const seedUrl = job.seed_urls[0];
        if (seedUrl !== undefined && !latest.has(seedUrl)) {
          latest.set(seedUrl, job);
        }
      }
      setLatestJobBySeedUrl(latest);
    } catch {
      // best-effort: seed rows just fall back to showing no last-run status
    }
  }, [selectedId]);

  useEffect(() => {
    void refreshSeeds();
    void refreshSeedJobs();
    setRunError(null);
    resetForm();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  function resetForm() {
    setUrlDraft("");
    setMaxDocuments(DEFAULT_MAX_DOCUMENTS);
    setMaxDepth(DEFAULT_MAX_DEPTH);
    setSameDomainOnly(false);
    setLanguage(DEFAULT_LANGUAGE);
    setEditingSeedId(null);
    setFormError(null);
  }

  function startEdit(seed: CrawlSeed) {
    setEditingSeedId(seed.id);
    setUrlDraft(seed.url);
    setMaxDocuments(seed.max_documents);
    setMaxDepth(seed.max_depth);
    setSameDomainOnly(seed.same_domain_only);
    setLanguage(seed.language);
    setFormError(null);
  }

  async function submitSeedForm() {
    if (selectedId === null) return;
    const trimmed = urlDraft.trim();
    if (!trimmed) return;
    setSavingSeed(true);
    setFormError(null);
    try {
      const input = {
        url: trimmed,
        max_documents: clampNumberInput(maxDocuments, 1, 2000),
        max_depth: clampNumberInput(maxDepth, 0, 5),
        same_domain_only: sameDomainOnly,
        language: (language.trim() || DEFAULT_LANGUAGE).toLowerCase(),
      };
      if (editingSeedId !== null) {
        await updateCrawlSeed(editingSeedId, input);
      } else {
        await createCrawlSeed(selectedId, input);
      }
      await refreshSeeds();
      resetForm();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setSavingSeed(false);
    }
  }

  async function removeSeed(seed: CrawlSeed) {
    setDeletingSeedId(seed.id);
    try {
      await deleteCrawlSeed(seed.id);
      if (editingSeedId === seed.id) resetForm();
      await refreshSeeds();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setDeletingSeedId(null);
    }
  }

  async function handleRunCrawl() {
    if (selectedId === null) return;
    if (isIndexing) {
      setRunError("Коллекция сейчас индексируется — дождитесь завершения индексации.");
      return;
    }
    if (seeds.length === 0) {
      setRunError("Добавьте хотя бы один адрес, чтобы начать обход.");
      return;
    }
    if (
      selected &&
      selected.document_count > 0 &&
      !window.confirm(
        `Коллекция «${selected.name}» уже содержит ${selected.document_count} документов. Запуск краулинга удалит их вместе с построенным индексом и начнёт сбор заново. Продолжить?`,
      )
    ) {
      return;
    }
    setRunning(true);
    setRunError(null);
    try {
      const jobs = await runCollectionCrawl(selectedId);
      setLatestJobBySeedUrl((prev) => {
        const next = new Map(prev);
        for (const job of jobs) {
          next.set(job.seed_urls[0], job);
        }
        return next;
      });
    } catch (err) {
      setRunError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  }

  // Only ever shows a task for a base URL that's still configured as a seed
  // — deleting a seed drops its last run from view too, in seed-list order.
  const visibleJobs = seeds
    .map((seed) => latestJobBySeedUrl.get(seed.url))
    .filter((job): job is CrawlJob => job !== undefined);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-lg font-semibold tracking-tight">
          <Waypoints className="size-5 text-muted-foreground" />
          Запуск краулинга
        </div>
        <Button asChild variant="ghost" size="icon" aria-label="Справка о краулинге" className="text-muted-foreground">
          <Link to="/help#crawling">
            <HelpCircle className="size-4" />
          </Link>
        </Button>
      </div>

      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end gap-2">
          <div className="flex min-w-[16rem] flex-1 flex-col gap-1.5">
            <Label className="flex items-center gap-1.5">
              <Link2 className="size-4 text-muted-foreground" />
              Адрес (URL)
            </Label>
            <div className="flex gap-1.5">
              <Input
                type="url"
                value={urlDraft}
                onChange={(e) => setUrlDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    void submitSeedForm();
                  }
                  if (e.key === "Escape" && editingSeedId !== null) {
                    resetForm();
                  }
                }}
                placeholder="https://example.com/"
              />
              {editingSeedId !== null && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={resetForm}
                  aria-label="Отменить редактирование"
                  className="shrink-0 text-muted-foreground"
                >
                  <X className="size-4" />
                </Button>
              )}
            </div>
          </div>

          <div className="flex w-32 flex-col gap-1.5">
            <Label className="flex items-center gap-1.5">
              <FileStack className="size-4 text-muted-foreground" />
              Документов
            </Label>
            <Input
              type="number"
              min={1}
              max={2000}
              value={maxDocuments}
              onChange={(e) => setMaxDocuments(e.target.value === "" ? "" : Number(e.target.value))}
              onBlur={() => setMaxDocuments((v) => clampNumberInput(v, 1, 2000))}
            />
          </div>

          <div className="flex w-28 flex-col gap-1.5">
            <Label className="flex items-center gap-1.5">
              <Layers className="size-4 text-muted-foreground" />
              Глубина
            </Label>
            <Input
              type="number"
              min={0}
              max={5}
              value={maxDepth}
              onChange={(e) => setMaxDepth(e.target.value === "" ? "" : Number(e.target.value))}
              onBlur={() => setMaxDepth((v) => clampNumberInput(v, 0, 5))}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label className="flex items-center gap-1.5">
              <Lock className="size-4 text-muted-foreground" />
              Только этот домен
            </Label>
            <div className="flex h-9 items-center justify-center">
              <Checkbox
                size="lg"
                checked={sameDomainOnly}
                onCheckedChange={(checked) => setSameDomainOnly(checked === true)}
              />
            </div>
          </div>

          <div className="flex flex-col items-center gap-1.5">
            <Label className="flex items-center gap-1.5">
              <Globe className="size-4 text-muted-foreground" />
              Язык
            </Label>
            <div className="flex h-9 items-center gap-1">
              {QUICK_LANGUAGES.map((code) => (
                <Button
                  key={code}
                  type="button"
                  size="sm"
                  variant={language === code ? "default" : "outline"}
                  onClick={() => setLanguage(code)}
                >
                  {code.toUpperCase()}
                </Button>
              ))}
              <Input
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                placeholder="en"
                maxLength={10}
                className="w-16"
                title="Присваивается документам, собранным по этому адресу"
              />
            </div>
          </div>

          <Button
            type="button"
            variant={editingSeedId !== null ? "default" : "outline"}
            size="icon"
            onClick={submitSeedForm}
            disabled={savingSeed}
            aria-label={editingSeedId !== null ? "Сохранить адрес" : "Добавить адрес"}
            className="shrink-0 transition-transform duration-150 hover:scale-105 active:scale-95"
          >
            {editingSeedId !== null ? <Check className="size-4" /> : <Plus className="size-4" />}
          </Button>
        </div>

        <div className="flex min-h-40 w-full flex-col rounded-md border">
          {seedsLoading ? (
            <p className="flex flex-1 items-center justify-center px-6 py-8 text-center text-xs text-muted-foreground">
              Загрузка…
            </p>
          ) : seeds.length === 0 ? (
            <p className="flex flex-1 items-center justify-center px-6 py-8 text-center text-xs text-muted-foreground">
              Добавьте хотя бы один адрес, чтобы начать обход.
            </p>
          ) : (
            <ScrollArea className="h-40 min-w-0">
              <div className="min-w-0 divide-y">
                {seeds.map((seed, index) => {
                  const lastJob = latestJobBySeedUrl.get(seed.url);
                  return (
                  <div
                    key={seed.id}
                    className={cn(
                      "flex items-center gap-2 px-3 py-2 text-xs transition-colors duration-150 hover:bg-muted/50",
                      editingSeedId === seed.id && "bg-accent/60",
                    )}
                  >
                    <span className="w-5 shrink-0 text-muted-foreground">{index + 1}.</span>
                    <span className="min-w-0 flex-1 truncate" title={seed.url}>
                      {seed.url}
                    </span>
                    <span className="hidden shrink-0 items-center gap-1 sm:flex">
                      <Badge variant="outline" className="gap-1 text-[10px]">
                        <Globe className="size-3" />
                        {seed.language.toUpperCase()}
                      </Badge>
                      <Badge variant="outline" className="gap-1 text-[10px]">
                        <FileStack className="size-3" />
                        {seed.max_documents}
                      </Badge>
                      <Badge variant="outline" className="gap-1 text-[10px]">
                        <Layers className="size-3" />
                        {seed.max_depth}
                      </Badge>
                      {seed.same_domain_only && (
                        <Badge variant="outline" className="gap-1 text-[10px]">
                          <Lock className="size-3" />
                          домен
                        </Badge>
                      )}
                      {lastJob && (
                        <Badge
                          variant="outline"
                          className={cn("gap-1 text-[10px]", STATUS_BADGE_CLASS[lastJob.status])}
                          title={
                            lastJob.finished_at
                              ? `Последний запуск: ${new Date(lastJob.finished_at).toLocaleString()}`
                              : undefined
                          }
                        >
                          {STATUS_LABELS[lastJob.status]}
                        </Badge>
                      )}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => startEdit(seed)}
                      aria-label="Редактировать адрес"
                      className="shrink-0 text-muted-foreground transition-all duration-150 hover:scale-110 hover:text-primary active:scale-95"
                    >
                      <Pencil className="size-3.5" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => removeSeed(seed)}
                      disabled={deletingSeedId === seed.id}
                      aria-label="Удалить адрес"
                      className="shrink-0 text-muted-foreground transition-all duration-150 hover:scale-110 hover:text-destructive active:scale-95"
                    >
                      <X className="size-3.5" />
                    </Button>
                  </div>
                  );
                })}
              </div>
            </ScrollArea>
          )}
        </div>

        {formError && <p className="text-sm text-destructive">{formError}</p>}
        {runError && <p className="text-sm text-destructive">{runError}</p>}

        <Button
          type="button"
          onClick={handleRunCrawl}
          disabled={running || selectedId === null || isIndexing}
          title={isIndexing ? "Коллекция сейчас индексируется" : undefined}
          size="lg"
          className="w-full overflow-hidden transition-all duration-300 hover:scale-[1.015] hover:shadow-lg hover:shadow-primary/30 active:scale-[0.98]"
        >
          <Play className="size-4" />
          {running ? "Запуск…" : "Запустить краулинг"}
        </Button>
      </div>

      {visibleJobs.map((job) => (
        <CrawlJobProgressCard key={job.id} jobId={job.id} />
      ))}
    </div>
  );
}
