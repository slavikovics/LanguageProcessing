import { HelpCircle, RotateCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { compareLangIdMethods, rerunLangIdComparison } from "../api/client";
import { LANG_ID_METHOD_LABELS, LANG_ID_METHODS, type LangIdMethod, type LangIdRunSummary } from "../api/types";

import { LangIdMethodComparisonTable } from "@/components/LangIdMethodComparisonTable";
import { LangIdSummaryBarChart } from "@/components/LangIdSummaryBarChart";
import { ModelSwatch } from "@/components/ModelSwatch";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { colorForModel } from "@/lib/modelColors";

export function LangIdMetricsSection({ collectionId }: { collectionId: number | null }) {
  const [methodKeys, setMethodKeys] = useState<LangIdMethod[]>([...LANG_ID_METHODS]);
  const [summaries, setSummaries] = useState<LangIdRunSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleMethod(method: LangIdMethod, checked: boolean) {
    setMethodKeys((prev) => (checked ? [...prev, method] : prev.filter((m) => m !== method)));
  }

  async function refresh(id: number, methods: LangIdMethod[], { rerun = false }: { rerun?: boolean } = {}) {
    if (methods.length === 0) {
      setSummaries([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = rerun ? await rerunLangIdComparison(id, methods) : await compareLangIdMethods(id, methods);
      setSummaries(result.summaries);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSummaries([]);
    } finally {
      setLoading(false);
    }
  }

  const methodKeysDependency = methodKeys.join(",");
  useEffect(() => {
    if (collectionId !== null)
      void refresh(collectionId, methodKeys);
    else
      setSummaries([]);
  }, [collectionId, methodKeysDependency]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold tracking-tight">Метрики классификации по языку</h2>
          <div className="flex flex-wrap gap-2">
            {collectionId !== null && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => refresh(collectionId, methodKeys, { rerun: true })}
                disabled={loading}
                title="Заново классифицирует тестовую выборку каждым из выбранных методов, затем пересчитывает метрики — может занять некоторое время"
              >
                <RotateCw className={loading ? "size-3.5 animate-spin" : "size-3.5"} />
                {loading ? "Обновление…" : "Обновить"}
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
              checked={methodKeys.includes(method)}
              onCheckedChange={(checked) => toggleMethod(method, checked === true)}
            />
            <ModelSwatch label={LANG_ID_METHOD_LABELS[method]} color={colorForModel(method)} />
          </label>
        ))}
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}

      {collectionId === null && (
        <p className="text-sm text-muted-foreground">
          Выберите коллекцию вверху страницы, чтобы увидеть метрики классификации по языку.
        </p>
      )}

      {collectionId !== null && summaries.length === 0 && !loading && (
        <p className="text-sm text-muted-foreground">
          Пока нет ни одного завершённого теста для этой коллекции. Разметьте документы и
          запустите тест на странице{" "}
          <Link to="/lang-id" className="text-primary underline-offset-2 hover:underline">
            «Определение языка»
          </Link>
          , либо нажмите «Обновить» здесь.
        </p>
      )}

      {summaries.length > 0 && (
        <div className="flex flex-col gap-6">
          <LangIdMethodComparisonTable summaries={summaries} />
          <div className="grid gap-4 sm:grid-cols-2">
            <LangIdSummaryBarChart
              summaries={summaries}
              valueOf={(s) => s.accuracy * 100}
              formatValue={(v) => `${v.toFixed(1)}%`}
              ariaLabel="Accuracy по методам"
            />
            <LangIdSummaryBarChart
              summaries={summaries}
              valueOf={(s) => s.f1 * 100}
              formatValue={(v) => `${v.toFixed(1)}%`}
              ariaLabel="F1 (macro) по методам"
            />
          </div>
        </div>
      )}
    </div>
  );
}
