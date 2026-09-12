import { Printer, Save } from "lucide-react";
import { useEffect, useState } from "react";

import { getTranslationRunWords } from "@/api/client";
import type { TranslationRun, TranslationRunWord } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PagedTable, type PagedTableColumn } from "@/components/PagedTable";
import { getPosStyle } from "@/lib/posTags";
import { escapeHtml, openPrintView } from "@/lib/printView";

const PAGE_SIZE = 20;

export function TranslationWordListTab({ run }: { run: TranslationRun | null }) {
  const [words, setWords] = useState<TranslationRunWord[]>([]);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPage(0);
    if (!run) {
      setWords([]);
      return;
    }
    setLoading(true);
    setError(null);
    getTranslationRunWords(run.id)
      .then(setWords)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, [run]);

  function handleSaveToFile() {
    const lines = [
      `Частотный словарь (${run!.source_lang.toUpperCase()} → ${run!.target_lang.toUpperCase()})`,
      "",
      "#\tСлово\tЛемма\tPOS\tЧастота\tПеревод",
      ...words.map(
        (word) =>
          `${word.rank}\t${word.surface}\t${word.lemma}\t${word.pos}\t${word.frequency}\t${
            word.translation ?? "—"
          }`,
      ),
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `translation-${run!.id}-words.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function handlePrint() {
    const rows = words
      .map(
        (word) => `
          <tr>
            <td>${word.rank}</td>
            <td>${escapeHtml(word.surface)}</td>
            <td>${escapeHtml(word.lemma)}</td>
            <td>${escapeHtml(word.pos)}</td>
            <td>${word.frequency}</td>
            <td>${escapeHtml(word.translation ?? "—")}</td>
          </tr>
        `,
      )
      .join("");
    openPrintView(
      "Частотный словарь",
      `
        <h1>Частотный словарь</h1>
        <p class="meta">${escapeHtml(run!.source_lang.toUpperCase())} → ${escapeHtml(run!.target_lang.toUpperCase())}</p>
        <table>
          <thead><tr><th>#</th><th>Слово</th><th>Лемма</th><th>POS</th><th>Частота</th><th>Перевод</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      `,
    );
  }

  if (!run) {
    return (
      <Card>
        <CardHeader className="text-center">
          <CardTitle>Нет выполненного перевода</CardTitle>
          <CardDescription>
            Сначала выполните перевод на вкладке «Перевод» — здесь появится упорядоченный по
            частоте встречаемости список слов исходного текста с переводом и грамматической
            информацией.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const totalPages = Math.max(1, Math.ceil(words.length / PAGE_SIZE));
  const pageRows = words.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const columns: PagedTableColumn<TranslationRunWord>[] = [
    { key: "rank", header: "#", className: "w-12", render: (word) => word.rank },
    { key: "surface", header: "Слово", render: (word) => <span className="font-medium">{word.surface}</span> },
    { key: "lemma", header: "Лемма", render: (word) => <span className="text-muted-foreground">{word.lemma}</span> },
    {
      key: "pos",
      header: "POS",
      render: (word) => {
        const style = getPosStyle(word.pos);
        return (
          <Badge
            variant="outline"
            style={{ backgroundColor: style.bg, borderColor: style.border, color: style.text }}
          >
            {word.pos}
          </Badge>
        );
      },
    },
    { key: "frequency", header: "Частота", render: (word) => word.frequency },
    {
      key: "translation",
      header: "Перевод",
      render: (word) =>
        word.translation ?? <span className="text-muted-foreground">— нет в словаре —</span>,
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Частотный словарь</h2>
          <p className="text-sm text-muted-foreground">
            Слова исходного текста, упорядоченные по убыванию частоты встречаемости, с частью речи
            и переводом на {run.target_lang.toUpperCase()}.
          </p>
        </div>
        {words.length > 0 && (
          <div className="flex shrink-0 gap-2">
            <Button type="button" variant="outline" size="sm" onClick={handleSaveToFile}>
              <Save className="size-3.5" />
              Сохранить в файл
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={handlePrint}>
              <Printer className="size-3.5" />
              Печать
            </Button>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <PagedTable
        columns={columns}
        rows={pageRows}
        getRowKey={(word) => `${word.lemma}-${word.pos}`}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        totalCount={words.length}
        totalLabel="Всего слов:"
        loading={loading}
        emptyMessage="В тексте нет значимых слов"
      />
    </div>
  );
}
