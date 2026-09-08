import { HelpCircle, Play, Waypoints } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { deleteCrawlSeed, listCrawlJobs, listCrawlSeeds, runCollectionCrawl } from "../api/client";
import type { CrawlJob, CrawlSeed } from "../api/types";

import { Button } from "@/components/ui/button";
import { CrawlJobProgressCard } from "@/components/CrawlJobProgressCard";
import { CrawlSeedForm } from "@/components/CrawlSeedForm";
import { CrawlSeedList } from "@/components/CrawlSeedList";
import { useCollectionContext } from "@/context/CollectionContext";

export function CrawlPage() {
  const { selected, selectedId, isIndexing } = useCollectionContext();

  const [seeds, setSeeds] = useState<CrawlSeed[]>([]);
  const [seedsLoading, setSeedsLoading] = useState(false);
  const [editingSeedId, setEditingSeedId] = useState<number | null>(null);
  const [deletingSeedId, setDeletingSeedId] = useState<number | null>(null);
  const [seedListError, setSeedListError] = useState<string | null>(null);

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
      setSeedListError(err instanceof Error ? err.message : String(err));
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
      for (const job of jobs) {
        const seedUrl = job.seed_urls[0];
        if (seedUrl !== undefined && !latest.has(seedUrl)) {
          latest.set(seedUrl, job);
        }
      }
      setLatestJobBySeedUrl(latest);
    } catch {}
  }, [selectedId]);

  useEffect(() => {
    void refreshSeeds();
    void refreshSeedJobs();
    setRunError(null);
    setEditingSeedId(null);
  }, [selectedId]);

  async function removeSeed(seed: CrawlSeed) {
    setDeletingSeedId(seed.id);
    try {
      await deleteCrawlSeed(seed.id);
      if (editingSeedId === seed.id) setEditingSeedId(null);
      await refreshSeeds();
    } catch (err) {
      setSeedListError(err instanceof Error ? err.message : String(err));
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
        `Коллекция «${selected.name}» уже содержит ${selected.document_count} документов. Запуск кроулинга удалит их вместе с построенным индексом и начнёт сбор заново. Продолжить?`,
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

  const visibleJobs = seeds
    .map((seed) => latestJobBySeedUrl.get(seed.url))
    .filter((job): job is CrawlJob => job !== undefined);

  const editingSeed = seeds.find((seed) => seed.id === editingSeedId) ?? null;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-lg font-semibold tracking-tight">
          <Waypoints className="size-5 text-muted-foreground" />
          Запуск кроулинга
        </div>
        <Button asChild variant="ghost" size="icon" aria-label="Справка о кроулинге" className="text-muted-foreground">
          <Link to="/help#crawling">
            <HelpCircle className="size-4" />
          </Link>
        </Button>
      </div>

      <div className="flex flex-col gap-3">
        <CrawlSeedForm
          collectionId={selectedId}
          editingSeed={editingSeed}
          onCancelEdit={() => setEditingSeedId(null)}
          onSaved={() => {
            setEditingSeedId(null);
            void refreshSeeds();
          }}
        />

        <CrawlSeedList
          seeds={seeds}
          loading={seedsLoading}
          latestJobBySeedUrl={latestJobBySeedUrl}
          editingSeedId={editingSeedId}
          onEdit={(seed) => setEditingSeedId(seed.id)}
          onDelete={removeSeed}
          deletingSeedId={deletingSeedId}
        />

        {seedListError && <p className="text-sm text-destructive">{seedListError}</p>}
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
          {running ? "Запуск…" : "Запустить кроулинг"}
        </Button>
      </div>

      {visibleJobs.map((job) => (
        <CrawlJobProgressCard key={job.id} jobId={job.id} />
      ))}
    </div>
  );
}
