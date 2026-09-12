import { Eye } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getTranslationRunSentences } from "@/api/client";
import type { TranslationRun } from "@/api/types";
import { PagedTable, type PagedTableColumn } from "@/components/PagedTable";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const PAGE_SIZE = 20;

interface IndexedSentence {
  index: number;
  text: string;
}

export function TranslationSyntaxTab({ run }: { run: TranslationRun | null }) {
  const [sentences, setSentences] = useState<IndexedSentence[]>([]);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setPage(0);
    if (!run) {
      setSentences([]);
      return;
    }
    setLoading(true);
    getTranslationRunSentences(run.id)
      .then((list) => setSentences(list.map((text, index) => ({ index, text }))))
      .finally(() => setLoading(false));
  }, [run]);

  if (!run) {
    return (
      <Card>
        <CardHeader className="text-center">
          <CardTitle>Нет выполненного перевода</CardTitle>
          <CardDescription>
            Сначала выполните перевод на вкладке «Перевод» — здесь появится список предложений
            исходного текста, для каждого из которых можно построить дерево синтаксического
            разбора.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const totalPages = Math.max(1, Math.ceil(sentences.length / PAGE_SIZE));
  const pageRows = sentences.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  function openReport(sentence: IndexedSentence) {
    navigate(`/translation/runs/${run!.id}/sentences/${sentence.index}`);
  }

  const columns: PagedTableColumn<IndexedSentence>[] = [
    { key: "index", header: "#", className: "w-16", render: (row) => row.index + 1 },
    { key: "text", header: "Предложение", align: "left", render: (row) => row.text },
    {
      key: "actions",
      header: "",
      className: "w-24",
      render: (row) => (
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label="Синтаксический разбор"
          onClick={(event) => {
            event.stopPropagation();
            openReport(row);
          }}
        >
          <Eye className="size-3.5" />
        </Button>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold">Предложения</h2>
        <p className="text-sm text-muted-foreground">
          Выберите предложение исходного текста, чтобы построить дерево синтаксического разбора.
        </p>
      </div>

      <PagedTable
        columns={columns}
        rows={pageRows}
        getRowKey={(row) => row.index}
        onRowClick={openReport}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        totalCount={sentences.length}
        totalLabel="Всего предложений:"
        loading={loading}
        emptyMessage="В тексте нет предложений"
      />
    </div>
  );
}
