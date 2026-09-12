import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { deleteTranslationDictionaryEntry, listTranslationDictionary } from "@/api/client";
import type { TranslationDictionaryEntry } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PagedTable, type PagedTableColumn } from "@/components/PagedTable";
import { TranslationDictionaryFormDialog } from "@/components/TranslationDictionaryFormDialog";

const PAGE_SIZE = 20;

export function TranslationDictionaryTab() {
  const [entries, setEntries] = useState<TranslationDictionaryEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [dialogMode, setDialogMode] = useState<"closed" | "create" | "edit">("closed");
  const [editingEntry, setEditingEntry] = useState<TranslationDictionaryEntry | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    listTranslationDictionary({ search: search || undefined, limit: PAGE_SIZE, offset: page * PAGE_SIZE })
      .then((result) => {
        setEntries(result.items);
        setTotal(result.total);
      })
      .finally(() => setLoading(false));
  }, [search, page]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    setPage(0);
  }, [search]);

  async function handleDelete(entry: TranslationDictionaryEntry) {
    if (!window.confirm(`Удалить «${entry.source_lemma} → ${entry.target_text}»?`)) return;
    await deleteTranslationDictionaryEntry(entry.id);
    refresh();
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const columns: PagedTableColumn<TranslationDictionaryEntry>[] = [
    { key: "source_lemma", header: "Слово", render: (entry) => <span className="font-medium">{entry.source_lemma}</span> },
    {
      key: "pos",
      header: "POS",
      render: (entry) =>
        entry.pos && entry.pos !== "*" ? (
          <Badge variant="outline">{entry.pos}</Badge>
        ) : (
          <span className="text-muted-foreground">любая</span>
        ),
    },
    { key: "target_text", header: "Перевод", render: (entry) => entry.target_text },
    {
      key: "actions",
      header: "",
      className: "w-24",
      render: (entry) => (
        <div className="flex justify-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="Редактировать"
            onClick={() => {
              setEditingEntry(entry);
              setDialogMode("edit");
            }}
          >
            <Pencil className="size-3.5" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="Удалить"
            onClick={() => handleDelete(entry)}
          >
            <Trash2 className="size-3.5" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold">Словарь переводов (EN → FR)</h2>
        <p className="text-sm text-muted-foreground">
          Утилита пополнения и корректировки словаря, используемого системой прямого (пословного)
          перевода — добавляйте отсутствующие слова или исправляйте переводы, чтобы повысить
          полноту перевода без переобучения какой-либо модели.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex min-w-64 flex-1 items-center gap-2">
          <Search className="size-4 shrink-0 text-muted-foreground" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Поиск по слову или переводу…"
          />
        </div>
        <Button
          type="button"
          onClick={() => {
            setEditingEntry(null);
            setDialogMode("create");
          }}
        >
          <Plus className="size-4" />
          Добавить слово
        </Button>
      </div>

      <PagedTable
        columns={columns}
        rows={entries}
        getRowKey={(entry) => entry.id}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        totalCount={total}
        totalLabel="Всего слов:"
        loading={loading}
        emptyMessage={search ? "Ничего не найдено" : "Словарь пуст"}
      />

      <TranslationDictionaryFormDialog
        mode={dialogMode}
        editingEntry={editingEntry}
        onClose={() => setDialogMode("closed")}
        onSaved={refresh}
      />
    </div>
  );
}
