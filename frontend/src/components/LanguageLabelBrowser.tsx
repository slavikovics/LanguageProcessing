import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { listDocuments, listUnlabeledDocuments, setLanguageLabel } from "../api/client";
import { LANG_ID_LANGUAGES, type DocumentSummary } from "../api/types";

import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 20;

export function LanguageLabelBrowser({
  collectionId,
  onLabeled,
}: {
  collectionId: number;
  /** Called after a label/split change is saved, so the parent can refresh
   * its label-progress stats. */
  onLabeled: () => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [savingId, setSavingId] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const docs = showAll
        ? await listDocuments(collectionId, { limit: PAGE_SIZE, offset })
        : await listUnlabeledDocuments(collectionId, { limit: PAGE_SIZE, offset });
      setDocuments(docs);
    } finally {
      setLoading(false);
    }
  }, [collectionId, offset, showAll]);

  useEffect(() => {
    setOffset(0);
  }, [collectionId, showAll]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function updateLabel(
    doc: DocumentSummary,
    patch: { confirmed_language?: string | null; corpus_split?: "train" | "test" | null },
  ) {
    setSavingId(doc.id);
    try {
      const updated = await setLanguageLabel(doc.id, {
        confirmed_language: patch.confirmed_language ?? doc.confirmed_language,
        corpus_split: patch.corpus_split ?? doc.corpus_split,
      });
      setDocuments((docs) => docs.map((d) => (d.id === doc.id ? updated : d)));
      onLabeled();
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-md border p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          Отметьте истинный язык документа и отнесите его к обучающей или тестовой выборке — без
          этого документ не попадёт ни в один профиль языка и не будет участвовать в тестировании.
        </p>
        <label className="flex shrink-0 items-center gap-2 text-xs whitespace-nowrap text-muted-foreground">
          <Switch checked={showAll} onCheckedChange={setShowAll} />
          Показывать все
        </label>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Загрузка…</p>
      ) : documents.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          {showAll ? "В коллекции нет документов." : "Неразмеченных документов не осталось."}
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {documents.map((doc) => (
            <div key={doc.id} className="flex flex-col gap-2 rounded-md border p-2.5 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium">{doc.title}</div>
                {doc.url && (
                  <a
                    href={doc.url}
                    target="_blank"
                    rel="noreferrer"
                    className="block truncate text-xs text-primary underline-offset-2 hover:underline"
                  >
                    {doc.url}
                  </a>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <div className="flex gap-1">
                  {LANG_ID_LANGUAGES.map((lang) => (
                    <Button
                      key={lang.code}
                      type="button"
                      size="sm"
                      variant={doc.confirmed_language === lang.code ? "default" : "outline"}
                      disabled={savingId === doc.id}
                      onClick={() => updateLabel(doc, { confirmed_language: lang.code })}
                    >
                      {lang.code.toUpperCase()}
                    </Button>
                  ))}
                </div>
                <div className="flex gap-1">
                  {(["train", "test"] as const).map((split) => (
                    <Button
                      key={split}
                      type="button"
                      size="sm"
                      variant={doc.corpus_split === split ? "default" : "outline"}
                      disabled={savingId === doc.id || doc.confirmed_language === null}
                      className={cn(
                        doc.corpus_split === split && "bg-emerald-600 hover:bg-emerald-600/90",
                      )}
                      onClick={() => updateLabel(doc, { corpus_split: split })}
                    >
                      {split === "train" ? "Обучение" : "Тест"}
                    </Button>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={offset === 0 || loading}
          onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
        >
          <ChevronLeft className="size-4" />
          Назад
        </Button>
        <span className="text-xs text-muted-foreground">
          {offset + 1}–{offset + documents.length}
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={loading || documents.length < PAGE_SIZE}
          onClick={() => setOffset((o) => o + PAGE_SIZE)}
        >
          Дальше
          <ChevronRight className="size-4" />
        </Button>
      </div>
    </div>
  );
}
