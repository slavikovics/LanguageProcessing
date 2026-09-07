import { HelpCircle, RotateCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { compareLangIdMethods, getMetricsComparison, rerunLangIdComparison, rerunMetricsComparison } from "../api/client";
import {
  LANG_ID_METHOD_LABELS,
  LANG_ID_METHODS,
  type CollectionMetricsSummary,
  type LangIdMethod,
  type LangIdRunSummary,
} from "../api/types";

import { CurveSeries, PrecisionRecallChart } from "@/components/PrecisionRecallChart";
import { LangIdMethodComparisonTable } from "@/components/LangIdMethodComparisonTable";
import { LangIdSummaryBarChart } from "@/components/LangIdSummaryBarChart";
import { MetricComparisonTable } from "@/components/MetricComparisonTable";
import { MetricsByQueryChart } from "@/components/MetricsByQueryChart";
import { ModelSwatch } from "@/components/ModelSwatch";
import type { QuerySeries } from "@/components/QueryMetricBarChart";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { useCollectionContext } from "@/context/CollectionContext";
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
    if (selectedId !== null) void refresh(selectedId, selectedModelKeys);
    else setSummaries([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, modelKeysDependency]);

  // -- language-classification metrics ------------------------------------
  const [langIdMethodKeys, setLangIdMethodKeys] = useState<LangIdMethod[]>([...LANG_ID_METHODS]);
  const [langIdSummaries, setLangIdSummaries] = useState<LangIdRunSummary[]>([]);
  const [langIdLoading, setLangIdLoading] = useState(false);
  const [langIdError, setLangIdError] = useState<string | null>(null);

  function toggleLangIdMethod(method: LangIdMethod, checked: boolean) {
    setLangIdMethodKeys((prev) => (checked ? [...prev, method] : prev.filter((m) => m !== method)));
  }

  async function refreshLangId(
    id: number,
    methods: LangIdMethod[],
    { rerun = false }: { rerun?: boolean } = {},
  ) {
    if (methods.length === 0) {
      setLangIdSummaries([]);
      return;
    }
    setLangIdLoading(true);
    setLangIdError(null);
    try {
      // "Обновить" runs a fresh classification pass for every selected
      // method (slower); toggles/initial load just read each method's
      // latest already-completed run.
      const result = rerun ? await rerunLangIdComparison(id, methods) : await compareLangIdMethods(id, methods);
      setLangIdSummaries(result.summaries);
    } catch (err) {
      setLangIdError(err instanceof Error ? err.message : String(err));
      setLangIdSummaries([]);
    } finally {
      setLangIdLoading(false);
    }
  }

  const langIdMethodKeysDependency = langIdMethodKeys.join(",");
  useEffect(() => {
    if (selectedId !== null) void refreshLangId(selectedId, langIdMethodKeys);
    else setLangIdSummaries([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, langIdMethodKeysDependency]);

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
      <Card>
        <CardHeader>
          <CardTitle>Метрики качества</CardTitle>
          <CardDescription>
            Оценка качества работы системы по каждой из решаемых задач — у каждой задачи свой
            раздел ниже: качество поиска и качество определения языка. В следующих лабораторных
            здесь появятся и другие разделы (например, качество реферирования).
          </CardDescription>
        </CardHeader>
      </Card>

      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold tracking-tight">Метрики поиска</h2>
            <div className="flex flex-wrap gap-2">
              {selectedId !== null && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => refresh(selectedId, selectedModelKeys, { rerun: true })}
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

        {selectedId === null && (
          <p className="text-sm text-muted-foreground">
            Выберите коллекцию вверху страницы, чтобы увидеть метрики качества поиска.
          </p>
        )}

        {selectedId !== null && withQueries.length === 0 && totalUnscored === 0 && !loading && (
          <p className="text-sm text-muted-foreground">
            Пока нет ни одного запроса с разметкой релевантности в этой коллекции. Выполните поиск
            на странице «Поиск» и отметьте найденные документы как релевантные — разметка (qrels)
            появится здесь автоматически.
          </p>
        )}

        {selectedId !== null && withQueries.length === 0 && totalUnscored > 0 && (
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

      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold tracking-tight">Метрики классификации по языку</h2>
            <div className="flex flex-wrap gap-2">
              {selectedId !== null && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => refreshLangId(selectedId, langIdMethodKeys, { rerun: true })}
                  disabled={langIdLoading}
                  title="Заново классифицирует тестовую выборку каждым из выбранных методов, затем пересчитывает метрики — может занять некоторое время"
                >
                  <RotateCw className={langIdLoading ? "size-3.5 animate-spin" : "size-3.5"} />
                  {langIdLoading ? "Обновление…" : "Обновить"}
                </Button>
              )}
              <Button type="button" variant="outline" size="sm" asChild>
                <Link to="/help#lang-id">
                  <HelpCircle className="size-3.5" />
                  Подробнее о методике
                </Link>
              </Button>
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            Accuracy, Precision/Recall/F1 (macro-усреднение по языкам) для каждого метода
            определения языка — считаются по тестовой выборке размеченных документов. Разметьте
            документы и запустите тест на странице «Определение языка».
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <span className="text-xs text-muted-foreground">Сравнить методы:</span>
          {LANG_ID_METHODS.map((method) => (
            <label key={method} className="flex items-center gap-1.5 text-sm">
              <Checkbox
                checked={langIdMethodKeys.includes(method)}
                onCheckedChange={(checked) => toggleLangIdMethod(method, checked === true)}
              />
              <ModelSwatch label={LANG_ID_METHOD_LABELS[method]} color={colorForModel(method)} />
            </label>
          ))}
        </div>
        {langIdError && <p className="text-sm text-destructive">{langIdError}</p>}

        {selectedId === null && (
          <p className="text-sm text-muted-foreground">
            Выберите коллекцию вверху страницы, чтобы увидеть метрики классификации по языку.
          </p>
        )}

        {selectedId !== null && langIdSummaries.length === 0 && !langIdLoading && (
          <p className="text-sm text-muted-foreground">
            Пока нет ни одного завершённого теста для этой коллекции. Разметьте документы и
            запустите тест на странице{" "}
            <Link to="/lang-id" className="text-primary underline-offset-2 hover:underline">
              «Определение языка»
            </Link>
            , либо нажмите «Обновить» здесь.
          </p>
        )}

        {langIdSummaries.length > 0 && (
          <div className="flex flex-col gap-6">
            <LangIdMethodComparisonTable summaries={langIdSummaries} />
            <div className="grid gap-4 sm:grid-cols-2">
              <LangIdSummaryBarChart
                summaries={langIdSummaries}
                valueOf={(s) => s.accuracy * 100}
                formatValue={(v) => `${v.toFixed(1)}%`}
                ariaLabel="Accuracy по методам"
              />
              <LangIdSummaryBarChart
                summaries={langIdSummaries}
                valueOf={(s) => s.f1 * 100}
                formatValue={(v) => `${v.toFixed(1)}%`}
                ariaLabel="F1 (macro) по методам"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
