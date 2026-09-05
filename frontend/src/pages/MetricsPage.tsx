import { HelpCircle, RotateCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getMetricsComparison } from "../api/client";
import type { CollectionMetricsSummary, QueryMetrics } from "../api/types";

import { CurveSeries, PrecisionRecallChart } from "@/components/PrecisionRecallChart";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCollectionContext } from "@/context/CollectionContext";
import { useSearchModelContext } from "@/context/SearchModelContext";
import { useMeasuredWidth } from "@/hooks/useMeasuredWidth";
import { colorForModel } from "@/lib/modelColors";

function ModelSwatch({ label, color }: { label: string; color: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-xs">
      <span className="inline-block size-2.5 shrink-0 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}

const HEADLINE_METRICS: { key: keyof CollectionMetricsSummary; label: string; hint?: string }[] = [
  { key: "map", label: "MAP", hint: "среднее AP по запросам" },
  { key: "mean_r_precision", label: "R-precision (среднее)", hint: "отсечка = число релевантных" },
  { key: "mean_precision_at_5", label: "P@5 (среднее)" },
  { key: "mean_precision_at_10", label: "P@10 (среднее)" },
];

const MICRO_METRICS: { key: keyof CollectionMetricsSummary; label: string }[] = [
  { key: "micro_precision", label: "Precision (микро)" },
  { key: "micro_recall", label: "Recall (микро)" },
  { key: "micro_f1", label: "F1 (микро, не из методики)" },
];

function MetricComparisonTable({
  summaries,
  metrics,
}: {
  summaries: CollectionMetricsSummary[];
  metrics: { key: keyof CollectionMetricsSummary; label: string; hint?: string }[];
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Метрика</TableHead>
          {summaries.map((s) => (
            <TableHead key={s.model} className="text-right">
              <ModelSwatch label={s.model_label} color={colorForModel(s.model)} />
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {metrics.map((m) => (
          <TableRow key={m.key}>
            <TableCell>
              <div className="flex flex-col">
                <span>{m.label}</span>
                {m.hint && <span className="text-[11px] text-muted-foreground/70">{m.hint}</span>}
              </div>
            </TableCell>
            {summaries.map((s) => (
              <TableCell key={s.model} className="text-right font-medium tabular-nums">
                {(s[m.key] as number).toFixed(3)}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

const RANKING_METRICS: { value: string; key: keyof QueryMetrics; label: string }[] = [
  { value: "ap", key: "average_precision", label: "AP" },
  { value: "r-prec", key: "r_precision", label: "R-Precision" },
  { value: "p5", key: "precision_at_5", label: "P@5" },
  { value: "p10", key: "precision_at_10", label: "P@10" },
];

const BAR_CHART_LEVELS = [0, 0.25, 0.5, 0.75, 1];
const BAR_LABEL_MAX_LINES = 3;
const BAR_LABEL_CHARS_PER_LINE = 12;

function wrapLabel(text: string, maxCharsPerLine = BAR_LABEL_CHARS_PER_LINE, maxLines = BAR_LABEL_MAX_LINES): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length > maxCharsPerLine && current) {
      lines.push(current);
      current = word;
    } else {
      current = candidate;
    }
  }
  if (current) lines.push(current);
  if (lines.length > maxLines) {
    const shown = lines.slice(0, maxLines);
    shown[maxLines - 1] = `${shown[maxLines - 1].slice(0, maxCharsPerLine - 1)}…`;
    return shown;
  }
  return lines;
}

interface QuerySeries {
  key: string;
  label: string;
  color: string;
  queries: QueryMetrics[];
}

function QueryMetricBarChart({
  series,
  metricKey,
  height = 380,
}: {
  series: QuerySeries[];
  metricKey: keyof QueryMetrics;
  height?: number;
}) {
  const { ref, width } = useMeasuredWidth<HTMLDivElement>();
  const padding = { top: 24, right: 16, bottom: 16 + BAR_LABEL_MAX_LINES * 13, left: 34 };
  const innerW = Math.max(0, width - padding.left - padding.right);
  const innerH = height - padding.top - padding.bottom;

  // Group by query TEXT, not query_id: different models' runs for "the
  // same" query have different search_run_ids (and possibly different
  // query rows only if pooling somehow diverged), so text is the stable
  // key to line up bars across models.
  const queryTexts: string[] = [];
  const seen = new Set<string>();
  for (const s of series) {
    for (const q of s.queries) {
      if (!seen.has(q.query_text)) {
        seen.add(q.query_text);
        queryTexts.push(q.query_text);
      }
    }
  }

  const n = queryTexts.length;
  const slotW = n > 0 ? innerW / n : 0;
  const groupW = Math.max(10, Math.min(120, slotW * 0.7));
  const barW = series.length > 0 ? groupW / series.length : groupW;
  const singleSeries = series.length === 1;

  const toY = (value: number) => padding.top + (1 - value) * innerH;

  return (
    <div ref={ref} className="w-full">
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label="Метрика по запросам">
          {BAR_CHART_LEVELS.map((level) => (
            <g key={level}>
              <line
                x1={padding.left}
                x2={width - padding.right}
                y1={toY(level)}
                y2={toY(level)}
                stroke="currentColor"
                className="text-border/40"
              />
              <text x={padding.left - 8} y={toY(level) + 3} textAnchor="end" className="fill-muted-foreground text-[10px]">
                {level.toFixed(2)}
              </text>
            </g>
          ))}
          <line
            x1={padding.left}
            x2={padding.left}
            y1={padding.top}
            y2={padding.top + innerH}
            stroke="currentColor"
            className="text-border"
          />
          <line
            x1={padding.left}
            x2={width - padding.right}
            y1={padding.top + innerH}
            y2={padding.top + innerH}
            stroke="currentColor"
            className="text-border"
          />
          {queryTexts.map((text, qi) => {
            const groupX = padding.left + qi * slotW + (slotW - groupW) / 2;
            const lines = wrapLabel(text);
            return (
              <g key={text}>
                {series.map((s, si) => {
                  const q = s.queries.find((qq) => qq.query_text === text);
                  if (!q) return null;
                  const value = q[metricKey] as number;
                  const x = groupX + si * barW;
                  const y = toY(value);
                  const barH = Math.max(0, padding.top + innerH - y);
                  return (
                    <g key={s.key}>
                      <title>{`${s.label} — ${text}: ${value.toFixed(2)}`}</title>
                      <rect x={x} y={y} width={Math.max(2, barW - 2)} height={barH} rx={2} fill={s.color} />
                      {singleSeries && (
                        <text
                          x={x + barW / 2}
                          y={y - 6}
                          textAnchor="middle"
                          className="fill-foreground text-[11px] font-medium tabular-nums"
                        >
                          {value.toFixed(2)}
                        </text>
                      )}
                    </g>
                  );
                })}
                {lines.map((line, li) => (
                  <text
                    key={li}
                    x={groupX + groupW / 2}
                    y={padding.top + innerH + 16 + li * 13}
                    textAnchor="middle"
                    className="fill-muted-foreground text-[10px]"
                  >
                    {line}
                  </text>
                ))}
              </g>
            );
          })}
        </svg>
      )}
      {series.length > 1 && (
        <div className="flex flex-wrap gap-3 pt-2">
          {series.map((s) => (
            <ModelSwatch key={s.key} label={s.label} color={s.color} />
          ))}
        </div>
      )}
    </div>
  );
}

function MetricsByQueryChart({ series }: { series: QuerySeries[] }) {
  return (
    <Tabs defaultValue="ap">
      <TabsList>
        {RANKING_METRICS.map((m) => (
          <TabsTrigger key={m.value} value={m.value}>
            {m.label}
          </TabsTrigger>
        ))}
      </TabsList>
      {RANKING_METRICS.map((m) => (
        <TabsContent key={m.value} value={m.value}>
          <QueryMetricBarChart series={series} metricKey={m.key} />
        </TabsContent>
      ))}
    </Tabs>
  );
}

export function MetricsPage() {
  const { selectedId } = useCollectionContext();
  const { models } = useSearchModelContext();
  const [selectedModelKeys, setSelectedModelKeys] = useState<string[]>([]);
  const [summaries, setSummaries] = useState<CollectionMetricsSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Default to comparing every active model once the registry loads.
  useEffect(() => {
    if (models.length > 0 && selectedModelKeys.length === 0) {
      setSelectedModelKeys(models.map((m) => m.key));
    }
  }, [models, selectedModelKeys.length]);

  function toggleModel(key: string, checked: boolean) {
    setSelectedModelKeys((prev) => (checked ? [...prev, key] : prev.filter((k) => k !== key)));
  }

  async function refresh(id: number, modelKeys: string[]) {
    if (modelKeys.length === 0) {
      setSummaries([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await getMetricsComparison(id, modelKeys);
      setSummaries(result.summaries);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSummaries([]);
    } finally {
      setLoading(false);
    }
  }

  const modelKeysDependency = selectedModelKeys.join(",");
  useEffect(() => {
    if (selectedId !== null) void refresh(selectedId, selectedModelKeys);
    else setSummaries([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, modelKeysDependency]);

  const withQueries = summaries.filter((s) => s.queries.length > 0);
  const withoutQueries = summaries.filter((s) => s.queries.length === 0);
  const totalUnscored = summaries.reduce((sum, s) => sum + s.unscored_judged_queries, 0);

  const curves: CurveSeries[] = withQueries.map((s) => ({
    key: s.model,
    label: s.model_label,
    color: colorForModel(s.model),
    points: s.curve,
  }));
  const querySeries: QuerySeries[] = withQueries.map((s) => ({
    key: s.model,
    label: s.model_label,
    color: colorForModel(s.model),
    queries: s.queries,
  }));
  const tableRows = withQueries.flatMap((s) =>
    s.queries.map((q) => ({ ...q, modelKey: s.model, modelLabel: s.model_label })),
  );

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">Метрики качества</CardTitle>
          <CardDescription>
            Метрики считаются только по запросам с проставленной вручную разметкой
            релевантности. Выполните поиск на странице «Поиск», отметьте документы, затем
            вернитесь сюда.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-wrap gap-2">
            {selectedId !== null && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => refresh(selectedId, selectedModelKeys)}
                disabled={loading}
              >
                <RotateCw className={loading ? "size-3.5 animate-spin" : "size-3.5"} />
                {loading ? "Обновление…" : "Обновить"}
              </Button>
            )}
            <Button type="button" variant="outline" size="sm" asChild>
              <Link to="/help#metrics">
                <HelpCircle className="size-3.5" />
                Подробнее о методике
              </Link>
            </Button>
          </div>
          {models.length > 1 && (
            <div className="flex flex-wrap items-center gap-4 border-t pt-3">
              <span className="text-xs text-muted-foreground">Сравнить модели:</span>
              {models.map((m) => (
                <label key={m.key} className="flex items-center gap-1.5 text-sm">
                  <Checkbox
                    checked={selectedModelKeys.includes(m.key)}
                    onCheckedChange={(checked) => toggleModel(m.key, checked === true)}
                  />
                  <ModelSwatch label={m.label} color={colorForModel(m.key)} />
                </label>
              ))}
            </div>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
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

      {selectedId !== null && withQueries.length === 0 && totalUnscored === 0 && !loading && (
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

      {selectedId !== null && withQueries.length === 0 && totalUnscored > 0 && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">
              {(() => {
                const n = totalUnscored;
                const mod10 = n % 10;
                const mod100 = n % 100;
                const word =
                  mod10 === 1 && mod100 !== 11
                    ? "запрос размечен"
                    : [2, 3, 4].includes(mod10) && ![12, 13, 14].includes(mod100)
                      ? "запроса размечено"
                      : "запросов размечено";
                return `${n} ${word}, но`;
              })()}{" "}
              ни для одного из них не отмечено ни одного релевантного документа — при нуле
              релевантных документов Precision/Recall/AP не определены (методика ROMIP), поэтому
              такие запросы не попадают в сводку. Отметьте 👍 хотя бы один найденный документ как
              релевантный на странице «Поиск», чтобы запрос учитывался в метриках.
            </p>
          </CardContent>
        </Card>
      )}

      {withQueries.length > 0 && (
        <>
          {withoutQueries.length > 0 && (
            <p className="text-xs text-muted-foreground">
              Ещё нет размеченных запросов для сравнения по модели
              {withoutQueries.length === 1 ? "" : "м"}:{" "}
              {withoutQueries.map((s) => s.model_label).join(", ")}. Выполните поиск с этой моделью
              на странице «Поиск» и отметьте документы.
            </p>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Метрики ранжирования</CardTitle>
              <CardDescription>
                Не зависят от числа результатов в поиске (Топ-K) — среднее по размеченным запросам.
                Как считаются — см. «Подробнее о методике» выше.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <MetricComparisonTable summaries={withQueries} metrics={HEADLINE_METRICS} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>11-точечная P/R-кривая (TREC)</CardTitle>
              <CardDescription>
                Интерполированная точность на 11 уровнях полноты, усреднённая по размеченным
                запросам — подробнее в{" "}
                <Link to="/help#metric-curve" className="text-primary underline-offset-2 hover:underline">
                  Справке
                </Link>
                .
              </CardDescription>
            </CardHeader>
            <CardContent>
              <PrecisionRecallChart curves={curves} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Метрики ранжирования по запросам</CardTitle>
              <CardDescription>Сравнение между запросами и моделями — выберите метрику</CardDescription>
            </CardHeader>
            <CardContent>
              <MetricsByQueryChart series={querySeries} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Метрики по запросам</CardTitle>
              <CardDescription>
                Строка — запрос под одной моделью. Слева — метрики ранжирования (не зависят от
                Топ-K), справа — Precision/Recall/F1 по всему ранжированному списку. Формулы и
                определения — в{" "}
                <Link to="/help#metrics" className="text-primary underline-offset-2 hover:underline">
                  Справке
                </Link>
                .
              </CardDescription>
            </CardHeader>
            <CardContent>
              {(() => {
                const table = (
                  <Table>
                    <TableHeader className="sticky top-0 z-10">
                      <TableRow>
                        <TableHead>Запрос</TableHead>
                        {withQueries.length > 1 && <TableHead>Модель</TableHead>}
                        <TableHead className="w-24">Релевантных</TableHead>
                        <TableHead className="w-16">AP</TableHead>
                        <TableHead className="w-20">R-Prec.</TableHead>
                        <TableHead className="w-16">P@5</TableHead>
                        <TableHead className="w-16">P@10</TableHead>
                        <TableHead
                          className="w-24 text-muted-foreground"
                          title="Документов в полном ранжировании с ненулевым сходством — не то, что показано на экране поиска"
                        >
                          В ранжир.
                        </TableHead>
                        <TableHead className="w-16 text-muted-foreground">P</TableHead>
                        <TableHead className="w-16 text-muted-foreground">R</TableHead>
                        <TableHead className="w-16 text-muted-foreground" title="Гармоническое среднее Precision и Recall">
                          F1
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {tableRows.map((q) => (
                        <TableRow key={`${q.modelKey}-${q.search_run_id}`}>
                          <TableCell className="max-w-xs truncate">{q.query_text}</TableCell>
                          {withQueries.length > 1 && (
                            <TableCell>
                              <ModelSwatch label={q.modelLabel} color={colorForModel(q.modelKey)} />
                            </TableCell>
                          )}
                          <TableCell>{q.relevant_count}</TableCell>
                          <TableCell className="font-medium">{q.average_precision.toFixed(2)}</TableCell>
                          <TableCell className="font-medium">{q.r_precision.toFixed(2)}</TableCell>
                          <TableCell className="font-medium">{q.precision_at_5.toFixed(2)}</TableCell>
                          <TableCell className="font-medium">{q.precision_at_10.toFixed(2)}</TableCell>
                          <TableCell className="text-muted-foreground">{q.retrieved_count}</TableCell>
                          <TableCell className="text-muted-foreground">{q.precision.toFixed(2)}</TableCell>
                          <TableCell className="text-muted-foreground">{q.recall.toFixed(2)}</TableCell>
                          <TableCell className="text-muted-foreground">{q.f1.toFixed(2)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                );
                return tableRows.length > 10 ? <ScrollArea className="h-96">{table}</ScrollArea> : table;
              })()}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Дополнительно: микроусреднённые Precision/Recall/F1</CardTitle>
              <CardDescription>
                Микроусреднение по всем размеченным запросам коллекции сразу — сначала
                суммируются найденные и релевантные документы по всем запросам, и только потом
                делятся друг на друга.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <MetricComparisonTable summaries={withQueries} metrics={MICRO_METRICS} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
