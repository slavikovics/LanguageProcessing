import { HelpCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getCollectionMetricsSummary } from "../api/client";
import type { CollectionMetricsSummary, QueryMetrics } from "../api/types";

import { PrecisionRecallChart } from "@/components/PrecisionRecallChart";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCollectionContext } from "@/context/CollectionContext";

function Stat({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-2xl font-semibold tabular-nums">{value.toFixed(3)}</span>
      <span className="text-xs text-muted-foreground">{label}</span>
      {hint && <span className="text-[11px] text-muted-foreground/70">{hint}</span>}
    </div>
  );
}

function ApBarList({ queries }: { queries: QueryMetrics[] }) {
  return (
    <div className="flex flex-col gap-2.5">
      {queries.map((q) => (
        <div key={q.query_id} className="flex items-center gap-2">
          <span className="w-28 shrink-0 truncate text-xs text-muted-foreground" title={q.query_text}>
            {q.query_text}
          </span>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
              style={{ width: `${Math.round(q.average_precision * 100)}%` }}
            />
          </div>
          <span className="w-10 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
            {q.average_precision.toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function MetricsPage() {
  const { selected, selectedId } = useCollectionContext();
  const [summary, setSummary] = useState<CollectionMetricsSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh(id: number) {
    setLoading(true);
    setError(null);
    try {
      setSummary(await getCollectionMetricsSummary(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (selectedId !== null) void refresh(selectedId);
    else setSummary(null);
  }, [selectedId]);

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">Метрики качества</CardTitle>
          <CardDescription className="flex flex-wrap items-center gap-x-1.5">
            <span>
              Метрики считаются только по запросам с проставленной вручную разметкой
              релевантности. Выполните поиск на странице «Поиск», отметьте документы, затем
              вернитесь сюда.
              {selected && ` Коллекция: ${selected.name}.`}
            </span>
            <Link
              to="/help"
              className="inline-flex items-center gap-1 text-primary underline-offset-2 hover:underline"
            >
              <HelpCircle className="size-3.5" />
              Подробнее о методике
            </Link>
          </CardDescription>
        </CardHeader>
        {selectedId !== null && (
          <CardContent className="flex flex-col gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-fit"
              onClick={() => refresh(selectedId)}
              disabled={loading}
            >
              {loading ? "Обновление…" : "Обновить"}
            </Button>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </CardContent>
        )}
      </Card>

      {selectedId === null && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">
              Выберите коллекцию вверху страницы, чтобы увидеть метрики качества поиска.
            </p>
          </CardContent>
        </Card>
      )}

      {summary && summary.queries.length === 0 && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">
              Пока нет ни одного запроса с разметкой релевантности в этой коллекции. Выполните поиск
              на странице «Поиск» и отметьте найденные документы как релевантные/нерелевантные —
              разметка (qrels) появится здесь автоматически.
            </p>
          </CardContent>
        </Card>
      )}

      {summary && summary.queries.length > 0 && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>
                Сводка по коллекции ({summary.queries.length}{" "}
                {summary.queries.length === 1 ? "тестовый запрос" : "тестовых запросов"})
              </CardTitle>
              <CardDescription>MAP — макроусреднение AP; Precision/Recall/F1 — микроусреднение (методика ROMIP для дорожки поиска)</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-8">
              <Stat label="MAP" value={summary.map} />
              <Stat label="Precision (микро)" value={summary.micro_precision} />
              <Stat label="Recall (микро)" value={summary.micro_recall} />
              <Stat label="F1 (микро)" value={summary.micro_f1} />
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>11-точечная P/R-кривая</CardTitle>
                <CardDescription>Усреднено по всем размеченным запросам (TREC)</CardDescription>
              </CardHeader>
              <CardContent className="flex justify-center">
                <PrecisionRecallChart curve={summary.curve} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Average Precision по запросам</CardTitle>
                <CardDescription>Сравнение качества ранжирования между запросами</CardDescription>
              </CardHeader>
              <CardContent>
                <ApBarList queries={summary.queries} />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Метрики по запросам</CardTitle>
              <CardDescription>
                Precision/Recall — по всему списку результатов; P@5/P@10 — точность на первых 5/10
              </CardDescription>
            </CardHeader>
            <CardContent>
              {(() => {
                const table = (
                  <Table>
                    <TableHeader className="sticky top-0 z-10">
                      <TableRow>
                        <TableHead>Запрос</TableHead>
                        <TableHead className="w-20">Найдено</TableHead>
                        <TableHead className="w-24">Релевантных</TableHead>
                        <TableHead className="w-16">P</TableHead>
                        <TableHead className="w-16">R</TableHead>
                        <TableHead className="w-16">F1</TableHead>
                        <TableHead className="w-16">P@5</TableHead>
                        <TableHead className="w-16">P@10</TableHead>
                        <TableHead className="w-16">AP</TableHead>
                        <TableHead className="w-20">R-Prec.</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {summary.queries.map((q) => (
                        <TableRow key={q.query_id}>
                          <TableCell className="max-w-xs truncate">{q.query_text}</TableCell>
                          <TableCell>{q.retrieved_count}</TableCell>
                          <TableCell>{q.relevant_count}</TableCell>
                          <TableCell>{q.precision.toFixed(2)}</TableCell>
                          <TableCell>{q.recall.toFixed(2)}</TableCell>
                          <TableCell>{q.f1.toFixed(2)}</TableCell>
                          <TableCell>{q.precision_at_5.toFixed(2)}</TableCell>
                          <TableCell>{q.precision_at_10.toFixed(2)}</TableCell>
                          <TableCell>{q.average_precision.toFixed(2)}</TableCell>
                          <TableCell>{q.r_precision.toFixed(2)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                );
                return summary.queries.length > 10 ? <ScrollArea className="h-96">{table}</ScrollArea> : table;
              })()}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
