import { FileUp, HelpCircle, Pencil, Plus, RefreshCw, RotateCw, Square, Trash2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  cancelCrawlJob,
  cancelIndexJob,
  createDocument,
  createIndexJob,
  deleteCollection,
  deleteDocument,
  getDocument,
  listDocuments,
  refreshCollection,
  updateDocument,
} from "../api/client";
import type { DocumentSummary } from "../api/types";
import { useCrawlJobProgress } from "../hooks/useCrawlJobProgress";
import { useIndexJobProgress } from "../hooks/useIndexJobProgress";

import { ProgressBar } from "@/components/ProgressBar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Pagination } from "@/components/ui/pagination";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { useCollectionContext } from "@/context/CollectionContext";

const PAGE_SIZE = 10;

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col items-center text-center">
      <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{label}</span>
      <span className="text-2xl leading-tight font-semibold tracking-tight tabular-nums">{value}</span>
    </div>
  );
}

/** Strips <script>/<style>, pulls <title> and body text out of an uploaded
 * HTML file — client-side, so picking a file gives immediate feedback
 * without a server round trip. */
function extractFromHtml(html: string): { title: string; text: string } {
  const doc = new DOMParser().parseFromString(html, "text/html");
  doc.querySelectorAll("script, style, noscript").forEach((el) => el.remove());
  const title = doc.querySelector("title")?.textContent?.trim() ?? "";
  const text = (doc.body?.textContent ?? "").replace(/\s+/g, " ").trim();
  return { title, text };
}

type FormMode = "closed" | "create" | "edit";

export function CollectionsPage() {
  const { selected, selectedId, latestIndexJob, refreshIndexStatus, refreshCollections } =
    useCollectionContext();
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [indexError, setIndexError] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const { progress: liveJob } = useIndexJobProgress(activeJobId);
  const [cancellingIndex, setCancellingIndex] = useState(false);

  const [refreshJobId, setRefreshJobId] = useState<number | null>(null);
  const { progress: refreshProgress } = useCrawlJobProgress(refreshJobId);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [cancellingRefresh, setCancellingRefresh] = useState(false);

  const [formMode, setFormMode] = useState<FormMode>("closed");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formTitle, setFormTitle] = useState("");
  const [formUrl, setFormUrl] = useState("");
  const [formText, setFormText] = useState("");
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [deletingCollection, setDeletingCollection] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const titleInputRef = useRef<HTMLInputElement>(null);

  const refreshDocuments = useCallback(async () => {
    if (selectedId === null) {
      setDocuments([]);
      return;
    }
    setLoading(true);
    try {
      setDocuments(await listDocuments(selectedId, { limit: PAGE_SIZE, offset: page * PAGE_SIZE }));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [selectedId, page]);

  // Document counts can go stale if they changed elsewhere (a crawl job
  // finishing in another tab) — always re-check on arrival.
  useEffect(() => {
    void refreshCollections();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setPage(0);
    setFormMode("closed");
  }, [selectedId]);

  useEffect(() => {
    void refreshDocuments();
  }, [refreshDocuments]);

  // Pick up an already-running job (e.g. left running from another tab) so
  // the progress bar shows live state as soon as the page opens.
  useEffect(() => {
    if (latestIndexJob && (latestIndexJob.status === "pending" || latestIndexJob.status === "running")) {
      setActiveJobId(latestIndexJob.id);
    }
  }, [latestIndexJob]);

  useEffect(() => {
    if (liveJob && (liveJob.status === "completed" || liveJob.status === "failed")) {
      void refreshIndexStatus();
      setActiveJobId(null);
    }
  }, [liveJob, refreshIndexStatus]);

  useEffect(() => {
    if (refreshProgress && ["completed", "failed", "cancelled"].includes(refreshProgress.job.status)) {
      void Promise.all([refreshCollections(), refreshDocuments()]);
      setRefreshJobId(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshProgress]);

  async function handleIndex() {
    if (selectedId === null) return;
    setIndexError(null);
    try {
      const job = await createIndexJob(selectedId);
      setActiveJobId(job.id);
      void refreshIndexStatus();
    } catch (err) {
      setIndexError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleRefreshCollection() {
    if (selectedId === null) return;
    setRefreshError(null);
    try {
      const job = await refreshCollection(selectedId);
      setRefreshJobId(job.id);
    } catch (err) {
      setRefreshError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleCancelIndex(jobId: number) {
    setCancellingIndex(true);
    setIndexError(null);
    try {
      await cancelIndexJob(jobId);
    } catch (err) {
      setIndexError(err instanceof Error ? err.message : String(err));
    } finally {
      setCancellingIndex(false);
    }
  }

  async function handleCancelRefresh(jobId: number) {
    setCancellingRefresh(true);
    setRefreshError(null);
    try {
      await cancelCrawlJob(jobId);
    } catch (err) {
      setRefreshError(err instanceof Error ? err.message : String(err));
    } finally {
      setCancellingRefresh(false);
    }
  }

  function openCreateForm() {
    setFormMode("create");
    setEditingId(null);
    setFormTitle("");
    setFormUrl("");
    setFormText("");
    setFormError(null);
  }

  async function openEditForm(doc: DocumentSummary) {
    setFormMode("edit");
    setEditingId(doc.id);
    setFormError(null);
    setFormTitle(doc.title);
    setFormUrl(doc.url ?? "");
    setFormText("Загрузка…");
    try {
      const detail = await getDocument(doc.id);
      setFormText(detail.clean_text);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
      setFormText("");
    }
  }

  function closeForm() {
    setFormMode("closed");
    setEditingId(null);
    setFormError(null);
  }

  async function handleHtmlFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const html = await file.text();
    const { title, text } = extractFromHtml(html);
    if (title) setFormTitle(title);
    setFormText(text);
  }

  async function handleFormSubmit(event: FormEvent) {
    event.preventDefault();
    if (selectedId === null) return;
    setFormSubmitting(true);
    setFormError(null);
    try {
      const input = { title: formTitle, url: formUrl.trim() || null, clean_text: formText };
      if (formMode === "create") {
        await createDocument(selectedId, input);
      } else if (formMode === "edit" && editingId !== null) {
        await updateDocument(editingId, input);
      }
      // Both branches touch Collection.documents_changed_at on the backend
      // (create changes document_count too) — refresh the shared context so
      // the stale-index badge and count update immediately, not just on
      // next navigation.
      await Promise.all([refreshCollections(), refreshDocuments()]);
      closeForm();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : String(err));
    } finally {
      setFormSubmitting(false);
    }
  }

  async function handleDeleteCollection() {
    if (!selected) return;
    if (
      !window.confirm(
        `Удалить коллекцию «${selected.name}» вместе со всеми документами, индексом и историей запросов? Это действие необратимо.`,
      )
    ) {
      return;
    }
    setDeletingCollection(true);
    try {
      await deleteCollection(selected.id);
      await refreshCollections();
    } catch (err) {
      window.alert(err instanceof Error ? err.message : String(err));
    } finally {
      setDeletingCollection(false);
    }
  }

  async function handleDelete(doc: DocumentSummary) {
    if (!window.confirm(`Удалить документ «${doc.title}»? Это действие необратимо.`)) return;
    setDeletingId(doc.id);
    try {
      await deleteDocument(doc.id);
      if (editingId === doc.id) closeForm();
      await Promise.all([refreshDocuments(), refreshCollections()]);
    } catch (err) {
      window.alert(err instanceof Error ? err.message : String(err));
    } finally {
      setDeletingId(null);
    }
  }

  if (selectedId === null || !selected) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Нет выбранной коллекции</CardTitle>
          <CardDescription>
            Создайте коллекцию через «+» у переключателя вверху страницы, или начните с краулинга —
            он предложит создать коллекцию автоматически.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const displayedJob = liveJob ?? latestIndexJob;
  const isIndexing = displayedJob?.status === "pending" || displayedJob?.status === "running";
  const isRefreshing = refreshProgress !== null && !["completed", "failed", "cancelled"].includes(refreshProgress.job.status);
  const isStale =
    displayedJob?.status === "completed" &&
    displayedJob.finished_at !== null &&
    selected.documents_changed_at !== null &&
    new Date(selected.documents_changed_at) > new Date(displayedJob.finished_at);

  const totalPages = Math.max(1, Math.ceil(selected.document_count / PAGE_SIZE));

  return (
    <div className="flex flex-col gap-6">
      <Card className="relative py-4">
        <Button
          asChild
          variant="ghost"
          size="icon-sm"
          aria-label="Справка о коллекциях"
          className="absolute top-3 right-3 text-muted-foreground"
        >
          <Link to="/help#collections">
            <HelpCircle className="size-4" />
          </Link>
        </Button>
        <CardContent className="flex flex-col items-center gap-3">
          <div className="mx-auto flex w-full flex-wrap items-start justify-center gap-x-12 gap-y-5">
            <Stat label="Коллекция" value={selected.name} />
            <Stat label="Документов" value={selected.document_count} />
            <Stat
              label="Терминов в индексе"
              value={displayedJob?.status === "completed" ? (displayedJob.terms_indexed ?? "—") : "—"}
            />
            <Stat
              label="Последняя индексация"
              value={
                displayedJob?.status === "completed" && displayedJob.finished_at
                  ? new Date(displayedJob.finished_at).toLocaleString()
                  : "не выполнялась"
              }
            />
          </div>
          {isStale && !isIndexing && (
            <span className="text-xs text-amber-600 dark:text-amber-400">
              Документы менялись после индексации — результаты поиска могут быть неточными.
            </span>
          )}
          {indexError && <p className="text-xs text-destructive">{indexError}</p>}
          {refreshError && <p className="text-xs text-destructive">{refreshError}</p>}
        </CardContent>

        <CardContent className="flex flex-wrap items-center justify-center gap-2 border-t pt-4">
          <Button
            type="button"
            variant="outline"
            onClick={handleDeleteCollection}
            disabled={deletingCollection || isIndexing || isRefreshing}
            title={isIndexing ? "Коллекция сейчас индексируется" : undefined}
            className="text-destructive hover:bg-destructive/10 hover:text-destructive"
          >
            <Trash2 className="size-4" />
            {deletingCollection ? "Удаление…" : "Удалить коллекцию"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={handleRefreshCollection}
            disabled={isRefreshing || isIndexing || selected.document_count === 0}
            title={isIndexing ? "Коллекция сейчас индексируется" : undefined}
          >
            <RefreshCw className="size-4" />
            {isRefreshing ? "Обновление…" : "Обновить"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={handleIndex}
            disabled={isIndexing || selected.document_count === 0}
          >
            <RotateCw className="size-4" />
            {isIndexing ? "Индексация…" : "Переиндексировать"}
          </Button>
          <Button type="button" onClick={openCreateForm}>
            <Plus className="size-4" />
            Добавить документ
          </Button>
        </CardContent>

        {isIndexing && displayedJob && (
          <CardContent className="flex flex-col gap-2 border-t pt-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">
                {displayedJob.status === "pending"
                  ? "Задача поставлена в очередь…"
                  : `Обработано документов: ${displayedJob.documents_processed} из ${displayedJob.documents_total}`}
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleCancelIndex(displayedJob.id)}
                disabled={cancellingIndex}
                className="shrink-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
              >
                <Square className="size-3.5" />
                {cancellingIndex ? "Прерывание…" : "Прервать"}
              </Button>
            </div>
            <ProgressBar
              value={displayedJob.documents_processed}
              max={Math.max(displayedJob.documents_total, 1)}
            />
          </CardContent>
        )}
        {displayedJob?.status === "failed" && (
          <CardContent className="border-t pt-4">
            <p className="text-sm text-destructive">Ошибка индексации: {displayedJob.error_message}</p>
          </CardContent>
        )}
        {displayedJob?.status === "cancelled" && (
          <CardContent className="border-t pt-4">
            <p className="text-sm text-muted-foreground">Индексация прервана.</p>
          </CardContent>
        )}
        {isRefreshing && refreshProgress && (
          <CardContent className="flex flex-col gap-2 border-t pt-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">
                Перезагружено документов: {refreshProgress.job.documents_fetched} из{" "}
                {refreshProgress.job.max_documents}
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleCancelRefresh(refreshProgress.job.id)}
                disabled={cancellingRefresh}
                className="shrink-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
              >
                <Square className="size-3.5" />
                {cancellingRefresh ? "Прерывание…" : "Прервать"}
              </Button>
            </div>
            <ProgressBar
              value={refreshProgress.job.documents_fetched}
              max={Math.max(refreshProgress.job.max_documents, 1)}
            />
          </CardContent>
        )}
      </Card>

      <div className="flex flex-col gap-4">
        {loading && <p className="text-sm text-muted-foreground">Загрузка…</p>}
        {!loading && documents.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Документов пока нет — запустите краулинг на странице «Краулинг» или добавьте документ
            вручную.
          </p>
        )}
        {documents.length > 0 && (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Заголовок</TableHead>
                  <TableHead>URL</TableHead>
                  <TableHead className="w-24">Символов</TableHead>
                  <TableHead className="w-40">Дата</TableHead>
                  <TableHead className="w-20">Действия</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell className="max-w-xs truncate">{doc.title}</TableCell>
                    <TableCell className="max-w-xs truncate">
                      {doc.url ? (
                        <a
                          href={doc.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-primary underline-offset-2 hover:underline"
                        >
                          {doc.url}
                        </a>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>{doc.char_count}</TableCell>
                    <TableCell>{new Date(doc.fetched_at).toLocaleString()}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => openEditForm(doc)}
                          aria-label="Редактировать"
                        >
                          <Pencil className="size-3.5" />
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => handleDelete(doc)}
                          disabled={deletingId === doc.id}
                          aria-label="Удалить"
                          className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                        >
                          <Trash2 className="size-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-1">
                <span className="text-xs text-muted-foreground">
                  Страница {page + 1} из {totalPages}
                </span>
                <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
              </div>
            )}
          </>
        )}
      </div>

      <Dialog
        open={formMode !== "closed"}
        onOpenChange={(open) => {
          if (!open) closeForm();
        }}
      >
        <DialogContent
          className="max-w-2xl"
          onOpenAutoFocus={(event) => {
            // Radix focuses the first tabbable field (the title input) on
            // open, which selects its whole value — collapse the caret to
            // the end instead of leaving the title highlighted.
            event.preventDefault();
            const el = titleInputRef.current;
            if (el) {
              el.focus({ preventScroll: true });
              const end = el.value.length;
              el.setSelectionRange(end, end);
            }
          }}
        >
          <DialogHeader>
            <DialogTitle>{formMode === "create" ? "Новый документ" : "Редактирование документа"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleFormSubmit} className="flex flex-col gap-3">
            <div className="grid gap-1.5">
              <Label>Заголовок</Label>
              <Input ref={titleInputRef} value={formTitle} onChange={(e) => setFormTitle(e.target.value)} required />
            </div>
            <div className="grid gap-1.5">
              <Label>
                URL <span className="text-muted-foreground">(необязательно)</span>
              </Label>
              <Input
                type="url"
                value={formUrl}
                onChange={(e) => setFormUrl(e.target.value)}
                placeholder="https://example.com/"
              />
            </div>
            <div className="grid gap-1.5">
              <div className="flex items-center justify-between">
                <Label>Текст документа</Label>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <FileUp className="size-3.5" />
                  Загрузить HTML-файл
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".html,.htm,text/html"
                  className="hidden"
                  onChange={handleHtmlFile}
                />
              </div>
              <Textarea
                value={formText}
                onChange={(e) => setFormText(e.target.value)}
                className="h-40"
                required
              />
            </div>
            {formError && <p className="text-sm text-destructive">{formError}</p>}
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={closeForm}>
                Отмена
              </Button>
              <Button type="submit" disabled={formSubmitting}>
                {formSubmitting ? "Сохранение…" : formMode === "create" ? "Создать" : "Сохранить"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
