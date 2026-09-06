import { ChevronLeft, ChevronRight, ThumbsUp } from "lucide-react";
import { useEffect, useState } from "react";
import { listDocuments } from "../api/client";
import type { DocumentSummary } from "../api/types";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const COLLECTION_DOCS_PAGE_SIZE = 20;

export function CollectionJudgmentBrowser({
  collectionId,
  documentTotal,
  excludeIds,
  judgments,
  onToggleRelevant,
}: {
  collectionId: number;
  documentTotal: number;
  excludeIds: Set<number>;
  judgments: Record<number, boolean>;
  onToggleRelevant: (documentId: number) => void;
}) {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listDocuments(collectionId, { limit: COLLECTION_DOCS_PAGE_SIZE, offset })
      .then((docs) => {
        if (!cancelled) setDocuments(docs);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [collectionId, offset]);

  const visible = documents.filter((doc) => !excludeIds.has(doc.id));

  return (
    <div className="flex flex-col gap-3 rounded-md border p-4">
      <p className="text-xs text-muted-foreground">
        Остальные документы коллекции — не входят в текущую выдачу. Отметьте здесь те, что
        релевантны запросу, но поиск их не нашёл: без этого Recall всегда будет считаться по
        документам, которые и так были найдены, то есть искусственно равен 1.
      </p>
      {loading ? (
        <p className="text-sm text-muted-foreground">Загрузка…</p>
      ) : (
        <div className="flex flex-col gap-2">
          {visible.length === 0 && (
            <p className="text-sm text-muted-foreground">
              На этой странице все документы уже есть в выдаче выше.
            </p>
          )}
          {visible.map((doc) => {
            const isRelevant = judgments[doc.id] ?? false;
            return (
              <div
                key={doc.id}
                className="flex items-center justify-between gap-3 rounded-md border p-2.5"
              >
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">{doc.title}</div>
                  {doc.url && (
                    <div className="truncate text-xs text-muted-foreground">{doc.url}</div>
                  )}
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => onToggleRelevant(doc.id)}
                  aria-label={isRelevant ? "Убрать отметку «релевантен»" : "Отметить как релевантный"}
                  aria-pressed={isRelevant}
                  className={cn(
                    "shrink-0 transition-all duration-150 hover:scale-110",
                    isRelevant && "bg-emerald-600/15 text-emerald-600 dark:text-emerald-400",
                  )}
                >
                  <ThumbsUp className="size-4" />
                </Button>
              </div>
            );
          })}
        </div>
      )}
      <div className="flex items-center justify-between">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={offset === 0 || loading}
          onClick={() => setOffset((o) => Math.max(0, o - COLLECTION_DOCS_PAGE_SIZE))}
        >
          <ChevronLeft className="size-4" />
          Назад
        </Button>
        <span className="text-xs text-muted-foreground">
          {Math.min(offset + 1, documentTotal)}–{Math.min(offset + documents.length, documentTotal)} из{" "}
          {documentTotal}
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={loading || offset + COLLECTION_DOCS_PAGE_SIZE >= documentTotal}
          onClick={() => setOffset((o) => o + COLLECTION_DOCS_PAGE_SIZE)}
        >
          Дальше
          <ChevronRight className="size-4" />
        </Button>
      </div>
    </div>
  );
}
