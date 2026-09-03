import { useEffect, useState } from "react";
import { createCollection, createCrawlJob, listCollections, listCrawlJobs } from "../api/client";
import { ProgressBar } from "../components/ProgressBar";
import { useCrawlJobProgress } from "../hooks/useCrawlJobProgress";
import type { Collection, CrawlJob } from "../api/types";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { Plus, X } from "lucide-react";

const STATUS_LABELS: Record<CrawlJob["status"], string> = {
  pending: "в очереди",
  running: "выполняется",
  completed: "завершён",
  failed: "ошибка",
  cancelled: "отменён",
};

const URL_STATUS_COLOR: Record<string, string> = {
  success: "text-emerald-600 dark:text-emerald-400",
  failed: "text-destructive",
  skipped: "text-destructive",
};

type CollectionMode = "existing" | "new";

export function CrawlPage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [collectionMode, setCollectionMode] = useState<CollectionMode>("existing");
  const [collectionId, setCollectionId] = useState<number | null>(null);
  const [newCollectionName, setNewCollectionName] = useState("");

  const [seedUrls, setSeedUrls] = useState<string[]>([]);
  const [urlDraft, setUrlDraft] = useState("");
  const [maxDocuments, setMaxDocuments] = useState(20);
  const [maxDepth, setMaxDepth] = useState(1);

  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [jobs, setJobs] = useState<CrawlJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const { progress, connection } = useCrawlJobProgress(selectedJobId);

  useEffect(() => {
    void refreshCollections();
    void refreshJobs();
  }, []);

  async function refreshCollections() {
    try {
      setCollections(await listCollections());
    } catch (err) {
      console.error(err);
    }
  }

  async function refreshJobs() {
    try {
      setJobs(await listCrawlJobs());
    } catch (err) {
      console.error(err);
    }
  }

  function addSeedUrl() {
    const trimmed = urlDraft.trim();
    if (!trimmed) return;
    setSeedUrls((urls) => [...urls, trimmed]);
    setUrlDraft("");
  }

  function removeSeedUrl(index: number) {
    setSeedUrls((urls) => urls.filter((_, i) => i !== index));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);

    const trimmedUrls = seedUrls.map((url) => url.trim()).filter(Boolean);
    if (trimmedUrls.length === 0) {
      setFormError("Укажите хотя бы один начальный URL.");
      return;
    }

    setSubmitting(true);
    try {
      let targetCollectionId: number;
      if (collectionMode === "new") {
        if (!newCollectionName.trim()) {
          setFormError("Введите название новой коллекции.");
          setSubmitting(false);
          return;
        }
        const created = await createCollection({ name: newCollectionName.trim(), language: "en" });
        targetCollectionId = created.id;
        await refreshCollections();
      } else {
        if (collectionId === null) {
          setFormError("Выберите коллекцию.");
          setSubmitting(false);
          return;
        }
        targetCollectionId = collectionId;
      }

      const job = await createCrawlJob({
        collection_id: targetCollectionId,
        seed_urls: trimmedUrls,
        max_documents: maxDocuments,
        max_depth: maxDepth,
      });
      await refreshJobs();
      setSelectedJobId(job.id);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Запуск краулинга</CardTitle>
          <CardDescription>
            Краулер обходит страницы вширь (BFS), начиная с указанных адресов, и сохраняет
            найденные документы в выбранную коллекцию — с учётом robots.txt и лимитов ниже.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex max-w-xl flex-col gap-5">
            <div className="grid gap-1.5">
              <Label>Коллекция</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant={collectionMode === "existing" ? "default" : "outline"}
                  onClick={() => setCollectionMode("existing")}
                >
                  Существующая
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={collectionMode === "new" ? "default" : "outline"}
                  onClick={() => setCollectionMode("new")}
                >
                  Новая
                </Button>
              </div>

              {collectionMode === "existing" ? (
                <Select
                  value={collectionId === null ? undefined : String(collectionId)}
                  onValueChange={(v) => setCollectionId(Number(v))}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="— выберите коллекцию —" />
                  </SelectTrigger>
                  <SelectContent>
                    {collections.map((c) => (
                      <SelectItem key={c.id} value={String(c.id)}>
                        {c.name} ({c.language})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <Input
                  type="text"
                  value={newCollectionName}
                  onChange={(e) => setNewCollectionName(e.target.value)}
                  placeholder="например, tech-news-en"
                />
              )}
              <p className="text-xs text-muted-foreground">
                Коллекция — это группа документов, в которую попадут скачанные страницы.
              </p>
            </div>

            <div className="grid gap-1.5">
              <Label>Начальные адреса (URL)</Label>
              <div className="flex gap-2">
                <Input
                  type="url"
                  value={urlDraft}
                  onChange={(e) => setUrlDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addSeedUrl();
                    }
                  }}
                  placeholder="https://example.com/"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={addSeedUrl}
                  aria-label="Добавить URL"
                >
                  <Plus className="size-4" />
                </Button>
              </div>

              {seedUrls.length > 0 && (
                <ul className="flex flex-col gap-1 rounded-md border p-1">
                  {seedUrls.map((url, index) => (
                    <li
                      key={index}
                      className="flex items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-muted"
                    >
                      <span className="flex-1 truncate">{url}</span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeSeedUrl(index)}
                        aria-label="Удалить URL"
                      >
                        <X className="size-4" />
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
              <p className="text-xs text-muted-foreground">
                Краулер начнёт обход с этих страниц (глубина 0).
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-1.5">
                <Label>Макс. документов</Label>
                <Input
                  type="number"
                  min={1}
                  max={2000}
                  value={maxDocuments}
                  onChange={(e) => setMaxDocuments(Number(e.target.value))}
                />
                <p className="text-xs text-muted-foreground">Остановка после N документов</p>
              </div>

              <div className="grid gap-1.5">
                <Label>Глубина обхода</Label>
                <Input
                  type="number"
                  min={0}
                  max={5}
                  value={maxDepth}
                  onChange={(e) => setMaxDepth(Number(e.target.value))}
                />
                <p className="text-xs text-muted-foreground">0 — только начальные страницы</p>
              </div>
            </div>

            {formError && <p className="text-sm text-destructive">{formError}</p>}

            <Button type="submit" disabled={submitting} className="w-fit">
              {submitting ? "Запуск…" : "Запустить краулинг"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Прогресс</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {selectedJobId === null && (
            <p className="text-sm text-muted-foreground">
              Выберите задачу ниже или запустите новый краулинг.
            </p>
          )}
          {progress && (
            <div className="flex flex-col gap-3">
              <p className="flex flex-wrap items-center gap-2 text-sm">
                Задача #{progress.job.id} — статус:{" "}
                <strong>{STATUS_LABELS[progress.job.status]}</strong>
                {connection !== "idle" && (
                  <Badge variant="outline">
                    {connection === "websocket" ? "● live" : "● polling"}
                  </Badge>
                )}
              </p>
              <ProgressBar
                value={progress.job.documents_fetched}
                max={progress.job.max_documents}
              />
              <div className="flex gap-2">
                <Badge variant="secondary">В очереди: {progress.job.urls_queued}</Badge>
                <Badge variant="secondary">Посещено: {progress.job.urls_visited}</Badge>
                <Badge variant="secondary">Ошибок: {progress.job.urls_failed}</Badge>
              </div>
              {progress.job.error_message && (
                <p className="text-sm text-destructive">{progress.job.error_message}</p>
              )}
              <h3 className="text-sm font-medium">Последние обработанные URL</h3>
              <ScrollArea className="h-64 rounded-md border">
                <ul className="flex flex-col gap-1 p-2">
                  {progress.recent_urls.map((u) => (
                    <li
                      key={u.id}
                      className="flex items-baseline gap-2 rounded px-2 py-1 text-sm hover:bg-muted"
                    >
                      <span
                        className={cn(
                          "text-xs font-semibold uppercase",
                          URL_STATUS_COLOR[u.status],
                        )}
                      >
                        {u.status}
                      </span>
                      <span className="text-muted-foreground">d{u.depth}</span>
                      <span className="flex-1 truncate">{u.url}</span>
                      {u.error && (
                        <span className="text-xs text-destructive">{u.error}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </ScrollArea>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Последние задачи</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Статус</TableHead>
                <TableHead>Прогресс</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.map((job) => (
                <TableRow
                  key={job.id}
                  className={cn(job.id === selectedJobId && "bg-muted")}
                >
                  <TableCell>{job.id}</TableCell>
                  <TableCell>{STATUS_LABELS[job.status]}</TableCell>
                  <TableCell>
                    {job.documents_fetched} / {job.max_documents}
                  </TableCell>
                  <TableCell>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() => setSelectedJobId(job.id)}
                    >
                      Следить
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
