import { HelpCircle, RotateCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getMetricsComparison, rerunMetricsComparison } from "../api/client";
import type { CollectionMetricsSummary } from "../api/types";

import { MetricComparisonTable } from "@/components/MetricComparisonTable";
import { MetricsByQueryChart } from "@/components/MetricsByQueryChart";
import { ModelSwatch } from "@/components/ModelSwatch";
import { CurveSeries, PrecisionRecallChart } from "@/components/PrecisionRecallChart";
import type { QuerySeries } from "@/components/QueryMetricBarChart";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { useSearchModelContext } from "@/context/SearchModelContext";
import { colorForModel } from "@/lib/modelColors";

const HEADLINE_METRICS: { key: keyof CollectionMetricsSummary; label: string; hint?: string }[] = [
  { key: "map", label: "MAP", hint: "среднее AP по запросам" },
  { key: "mean_r_precision", label: "R-precision (среднее)", hint: "отсечка = число релевантных" },
  { key: "mean_precision_at_5", label: "P@5 (среднее)" },
  { key: "mean_precision_at_10", label: "P@10 (среднее)" },
  { key: "mean_recall_at_5", label: "R@5 (среднее)" },
  { key: "mean_recall_at_10", label: "R@10 (среднее)" },
  { key: "mean_f1_at_5", label: "F1@5 (среднее)" },
  { key: "mean_f1_at_10", label: "F1@10 (среднее)" },
];

export function SearchMetricsSection({ collectionId }: { collectionId: number | null }) {
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

  async function refresh(id: number, modelKeys: string[], { rerun = false }: { rerun?: boolean } = {}) {
    if (modelKeys.length === 0) {
      setSummaries([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // "Обновить" reruns every judged query against every selected model
      // (real searches, slower); toggles/initial load just recompute from
      // whatever already ran.
      const result = rerun ? await rerunMetricsComparison(id, modelKeys) : await getMetricsComparison(id, modelKeys);
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
    if (collectionId !== null) void refresh(collectionId, selectedModelKeys);
    else setSummaries([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [collectionId, modelKeysDependency]);

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

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold tracking-tight">Метрики поиска</h2>
          <div className="flex flex-wrap gap-2">
            {collectionId !== null && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => refresh(collectionId, selectedModelKeys, { rerun: true })}
                disabled={loading}
                title="Заново выполняет все размеченные запросы для каждой из выбранных моделей, затем пересчитывает метрики — может занять некоторое время"
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
        </div>
        <p className="text-sm text-muted-foreground">
          Метрики считаются только по запросам с проставленной вручную разметкой
          релевантности. Выполните поиск на странице «Поиск», отметьте документы, затем
          вернитесь сюда.
        </p>
      </div>

      {models.length > 1 && (
        <div className="flex flex-wrap items-center gap-4">
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

      {collectionId === null && (
        <p className="text-sm text-muted-foreground">
          Выберите коллекцию вверху страницы, чтобы увидеть метрики качества поиска.
        </p>
      )}

      {collectionId !== null && withQueries.length === 0 && totalUnscored === 0 && !loading && (
        <p className="text-sm text-muted-foreground">
          Пока нет ни одного запроса с разметкой релевантности в этой коллекции. Выполните поиск
          на странице «Поиск» и отметьте найденные документы как релевантные — разметка (qrels)
          появится здесь автоматически.
        </p>
      )}

      {collectionId !== null && withQueries.length === 0 && totalUnscored > 0 && (
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

          <div className="flex flex-col gap-3 border-t pt-6">
            <div>
              <h3 className="text-base font-semibold">Метрики ранжирования</h3>
              <p className="text-sm text-muted-foreground">
                Не зависят от числа результатов в поиске (Топ-K) — среднее по размеченным
                запросам. Как считаются — см. «Подробнее о методике» выше.
              </p>
            </div>
            <MetricComparisonTable summaries={withQueries} metrics={HEADLINE_METRICS} />
          </div>

          <div className="flex flex-col gap-3 border-t pt-6">
            <div>
              <h3 className="text-base font-semibold">11-точечная P/R-кривая (TREC)</h3>
              <p className="text-sm text-muted-foreground">
                Интерполированная точность на 11 уровнях полноты, усреднённая по размеченным
                запросам — подробнее в{" "}
                <Link to="/help#metric-curve" className="text-primary underline-offset-2 hover:underline">
                  Справке
                </Link>
                .
              </p>
            </div>
            <PrecisionRecallChart curves={curves} />
          </div>

          <div className="flex flex-col gap-3 border-t pt-6">
            <div>
              <h3 className="text-base font-semibold">Метрики ранжирования по запросам</h3>
              <p className="text-sm text-muted-foreground">
                Сравнение между запросами и моделями — выберите метрику
              </p>
            </div>
            <MetricsByQueryChart series={querySeries} />
          </div>
        </>
      )}
    </div>
  );
}
