import { HelpCircle, Split } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  autoSplitTrainTest,
  buildAlphabeticProfile,
  buildFrequentWordsProfile,
  compareLangIdMethods,
  createLangIdRuns,
  getLabelProgress,
  listDocuments,
  listLangIdProfiles,
  listLangIdResults,
} from "../api/client";
import {
  LANG_ID_LANGUAGES,
  LANG_ID_METHODS,
  LANG_ID_METHOD_LABELS,
  type DocumentSummary,
  type LabelProgress,
  type LangIdMethod,
  type LangIdProfile,
  type LangIdResult,
  type LangIdRunSummary,
} from "../api/types";
import { downloadCsv, downloadJson } from "../lib/exportResults";
import { useLangIdRunProgress } from "../hooks/useLangIdRunProgress";

import { AdHocClassifyPanel } from "@/components/AdHocClassifyPanel";
import { LangIdMethodComparisonTable } from "@/components/LangIdMethodComparisonTable";
import { LangIdResultsTable } from "@/components/LangIdResultsTable";
import { LangIdSummaryBarChart } from "@/components/LangIdSummaryBarChart";
import { LanguageLabelBrowser } from "@/components/LanguageLabelBrowser";
import { NeuralTrainingPanel } from "@/components/NeuralTrainingPanel";
import { ProgressBar } from "@/components/ProgressBar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCollectionContext } from "@/context/CollectionContext";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col items-center text-center">
      <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{label}</span>
      <span className="text-2xl leading-tight font-semibold tracking-tight tabular-nums">{value}</span>
    </div>
  );
}

const EMPTY_RUN_IDS: Record<LangIdMethod, number | null> = {
  frequent_words: null,
  alphabetic: null,
  neural: null,
};

export function LanguageIdPage() {
  const { selected, selectedId } = useCollectionContext();

  // -- labeling --------------------------------------------------------
  const [labelProgress, setLabelProgress] = useState<LabelProgress | null>(null);
  const refreshLabelProgress = useCallback(async () => {
    if (selectedId === null) {
      setLabelProgress(null);
      return;
    }
    setLabelProgress(await getLabelProgress(selectedId));
  }, [selectedId]);
  useEffect(() => {
    void refreshLabelProgress();
  }, [refreshLabelProgress]);

  const [autoSplitting, setAutoSplitting] = useState(false);
  const [autoSplitError, setAutoSplitError] = useState<string | null>(null);
  const [autoSplitMessage, setAutoSplitMessage] = useState<string | null>(null);
  // Bumped after an auto-split to force LanguageLabelBrowser to remount and
  // refetch — it otherwise only reloads on its own paging/filter changes,
  // so it wouldn't notice documents this action just split behind its back.
  const [labelBrowserKey, setLabelBrowserKey] = useState(0);

  async function handleAutoSplit() {
    if (selectedId === null) return;
    setAutoSplitting(true);
    setAutoSplitError(null);
    setAutoSplitMessage(null);
    try {
      const result = await autoSplitTrainTest(selectedId);
      setAutoSplitMessage(
        `Разбито ${result.train_assigned + result.test_assigned} документов: ${result.train_assigned} в обучающую, ${result.test_assigned} в тестовую выборку.`,
      );
      await refreshLabelProgress();
      setLabelBrowserKey((k) => k + 1);
    } catch (err) {
      setAutoSplitError(err instanceof Error ? err.message : String(err));
    } finally {
      setAutoSplitting(false);
    }
  }

  // -- profiles ----------------------------------------------------------
  const [profiles, setProfiles] = useState<LangIdProfile[]>([]);
  const refreshProfiles = useCallback(async () => {
    setProfiles(await listLangIdProfiles());
  }, []);
  useEffect(() => {
    void refreshProfiles();
  }, [refreshProfiles]);

  const [buildingKey, setBuildingKey] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);

  async function handleBuildLexicalProfile(method: "frequent_words" | "alphabetic", language: string) {
    setBuildingKey(`${method}:${language}`);
    setProfileError(null);
    try {
      if (method === "frequent_words") await buildFrequentWordsProfile(language);
      else await buildAlphabeticProfile(language);
      await refreshProfiles();
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : String(err));
    } finally {
      setBuildingKey(null);
    }
  }

  const neuralProfile = profiles.find((p) => p.method === "neural");
  const lexicalProfile = (method: "frequent_words" | "alphabetic", language: string) =>
    profiles.find((p) => p.method === method && p.language === language);

  // -- testing -------------------------------------------------------
  const [runIds, setRunIds] = useState<Record<LangIdMethod, number | null>>(EMPTY_RUN_IDS);
  const [testing, setTesting] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [summaries, setSummaries] = useState<LangIdRunSummary[]>([]);
  const [resultsByMethod, setResultsByMethod] = useState<Partial<Record<LangIdMethod, LangIdResult[]>>>({});
  const [testDocuments, setTestDocuments] = useState<DocumentSummary[]>([]);

  const { progress: freqWordsRun } = useLangIdRunProgress(runIds.frequent_words);
  const { progress: alphabeticRun } = useLangIdRunProgress(runIds.alphabetic);
  const { progress: neuralRun } = useLangIdRunProgress(runIds.neural);
  const runsInProgress = { frequent_words: freqWordsRun, alphabetic: alphabeticRun, neural: neuralRun };

  // Loads each method's latest completed run for the selected collection —
  // used both right after a fresh test finishes and to restore results when
  // this page is revisited (results live only in this component's state, so
  // navigating away and back would otherwise leave the testing tab empty
  // even though the runs are already persisted server-side).
  const loadLatestResults = useCallback(async () => {
    if (selectedId === null) {
      setSummaries([]);
      setResultsByMethod({});
      setTestDocuments([]);
      return;
    }
    const compared = await compareLangIdMethods(selectedId, [...LANG_ID_METHODS]);
    setSummaries(compared.summaries);
    const byMethod: Partial<Record<LangIdMethod, LangIdResult[]>> = {};
    for (const summary of compared.summaries) {
      byMethod[summary.method] = await listLangIdResults(summary.run_id);
    }
    setResultsByMethod(byMethod);
    const docs = await listDocuments(selectedId, { limit: 500 });
    setTestDocuments(docs.filter((d) => d.corpus_split === "test"));
  }, [selectedId]);

  useEffect(() => {
    void loadLatestResults();
  }, [loadLatestResults]);

  const finishTesting = useCallback(async () => {
    setTesting(false);
    setRunIds(EMPTY_RUN_IDS);
    await loadLatestResults();
  }, [loadLatestResults]);

  useEffect(() => {
    if (!testing) return;
    const runs = [freqWordsRun, alphabeticRun, neuralRun].filter((r) => r !== null);
    if (runs.length === 0) return;
    const allTerminal = runs.every((r) => r.status === "completed" || r.status === "failed");
    if (allTerminal) void finishTesting();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [freqWordsRun, alphabeticRun, neuralRun, testing]);

  async function handleRunTest() {
    if (selectedId === null) return;
    setRunError(null);
    setTesting(true);
    setSummaries([]);
    setResultsByMethod({});
    try {
      const runs = await createLangIdRuns(selectedId, [...LANG_ID_METHODS]);
      const next = { ...EMPTY_RUN_IDS };
      for (const run of runs) next[run.method] = run.id;
      setRunIds(next);
    } catch (err) {
      setRunError(err instanceof Error ? err.message : String(err));
      setTesting(false);
    }
  }

  function handleExportCsv() {
    const rows = testDocuments.map((doc) => {
      const row: Record<string, unknown> = {
        document: doc.title,
        url: doc.url ?? "",
        true_language: doc.confirmed_language ?? "",
      };
      for (const method of LANG_ID_METHODS) {
        const result = resultsByMethod[method]?.find((r) => r.document_id === doc.id);
        row[`${method}_predicted`] = result?.predicted_language ?? "";
        row[`${method}_correct`] = result?.is_correct ?? "";
      }
      return row;
    });
    downloadCsv("lang-id-results.csv", rows);
  }

  function handleExportJson() {
    downloadJson("lang-id-results.json", { summaries, results: resultsByMethod, documents: testDocuments });
  }

  if (selectedId === null || !selected) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Нет выбранной коллекции</CardTitle>
          <CardDescription>
            Выберите или создайте коллекцию через переключатель вверху страницы — язык
            определяется для документов конкретной коллекции.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Card className="relative py-4">
        <Button
          asChild
          variant="ghost"
          size="icon-sm"
          aria-label="Справка об определении языка"
          className="absolute top-3 right-3 text-muted-foreground"
        >
          <Link to="/help#lang-id">
            <HelpCircle className="size-4" />
          </Link>
        </Button>
        <CardHeader>
          <CardTitle>Определение языка текста</CardTitle>
          <CardDescription>
            Методы частотных слов, алфавитный и нейросетевой — разметьте документы, постройте
            профили языков, затем сравните методы на тестовой выборке.
          </CardDescription>
        </CardHeader>
      </Card>

      <Tabs defaultValue="labeling">
        <TabsList>
          <TabsTrigger value="labeling">Разметка</TabsTrigger>
          <TabsTrigger value="profiles">Профили</TabsTrigger>
          <TabsTrigger value="adhoc">Ручная проверка</TabsTrigger>
          <TabsTrigger value="testing">Тестирование</TabsTrigger>
        </TabsList>

        <TabsContent value="labeling" className="flex flex-col gap-4 pt-4">
          {labelProgress && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between gap-3">
                <CardTitle className="text-base">Прогресс разметки</CardTitle>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAutoSplit}
                  disabled={
                    autoSplitting ||
                    labelProgress.labeled - labelProgress.train_count - labelProgress.test_count <= 0
                  }
                  title="Автоматически разбивает документы с подтверждённым языком, но без выборки, на обучающую (80%) и тестовую (20%) — раздельно по каждому языку. Уже размеченные вручную документы не трогает."
                >
                  <Split className="size-3.5" />
                  {autoSplitting ? "Разбиение…" : "Разбить автоматически"}
                </Button>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-5">
                  <Stat label="Всего документов" value={labelProgress.total} />
                  <Stat label="Размечено" value={labelProgress.labeled} />
                  <Stat label="Не размечено" value={labelProgress.unlabeled} />
                  <Stat label="Обучающая выборка" value={labelProgress.train_count} />
                  <Stat label="Тестовая выборка" value={labelProgress.test_count} />
                </div>
                {autoSplitError && <p className="text-sm text-destructive">{autoSplitError}</p>}
                {autoSplitMessage && <p className="text-sm text-muted-foreground">{autoSplitMessage}</p>}
              </CardContent>
            </Card>
          )}
          <LanguageLabelBrowser key={labelBrowserKey} collectionId={selectedId} onLabeled={refreshLabelProgress} />
        </TabsContent>

        <TabsContent value="profiles" className="flex flex-col gap-4 pt-4">
          {(["frequent_words", "alphabetic"] as const).map((method) => (
            <Card key={method}>
              <CardHeader>
                <CardTitle>{LANG_ID_METHOD_LABELS[method]}</CardTitle>
                <CardDescription>Профиль строится по всем документам обучающей выборки, размеченным этим языком.</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-wrap justify-center gap-3">
                {LANG_ID_LANGUAGES.map((lang) => {
                  const profile = lexicalProfile(method, lang.code);
                  const key = `${method}:${lang.code}`;
                  return (
                    <div key={lang.code} className="flex flex-col gap-2 rounded-md border p-3">
                      <span className="text-sm font-medium">{lang.label}</span>
                      <span className="text-xs text-muted-foreground">
                        {profile
                          ? `${profile.source_document_count} документов · ${new Date(profile.built_at).toLocaleString()}`
                          : "Профиль не построен"}
                      </span>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={buildingKey === key}
                        onClick={() => handleBuildLexicalProfile(method, lang.code)}
                      >
                        {buildingKey === key ? "Строим…" : "Построить"}
                      </Button>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          ))}
          <NeuralTrainingPanel profile={neuralProfile} onTrained={refreshProfiles} />
          {profileError && <p className="text-sm text-destructive">{profileError}</p>}
        </TabsContent>

        <TabsContent value="adhoc" className="pt-4">
          <AdHocClassifyPanel />
        </TabsContent>

        <TabsContent value="testing" className="flex flex-col gap-4 pt-4">
          <Card>
            <CardContent className="flex flex-col gap-4 py-4">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="max-w-prose text-sm text-muted-foreground">
                  Все три метода — частотных слов, алфавитный и нейросетевой — запускаются на
                  документах тестовой выборки текущей коллекции. По завершении будут показаны
                  Accuracy, Precision, Recall, F1 и среднее время классификации каждого метода, а
                  также результат по каждому документу с экспортом в CSV/JSON и печатью.
                </p>
                <Button
                  type="button"
                  onClick={handleRunTest}
                  disabled={testing}
                  className="shrink-0 self-start sm:self-center"
                >
                  {testing ? "Тестирование…" : "Запустить тест"}
                </Button>
              </div>
              {runError && <p className="text-sm text-destructive">{runError}</p>}
              {testing && (
                <div className="flex flex-col gap-2">
                  {LANG_ID_METHODS.map((method) => {
                    const run = runsInProgress[method];
                    return (
                      <div key={method} className="flex flex-col gap-1">
                        <span className="text-xs text-muted-foreground">{LANG_ID_METHOD_LABELS[method]}</span>
                        <ProgressBar
                          value={run?.documents_processed ?? 0}
                          max={Math.max(run?.documents_total ?? 1, 1)}
                          complete={run?.status === "completed"}
                        />
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          {summaries.length > 0 && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>Сравнение методов</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-6">
                  <LangIdMethodComparisonTable summaries={summaries} />
                  <div className="grid gap-4 sm:grid-cols-2">
                    <LangIdSummaryBarChart
                      summaries={summaries}
                      valueOf={(s) => s.accuracy * 100}
                      formatValue={(v) => `${v.toFixed(1)}%`}
                      ariaLabel="Точность по методам"
                    />
                    <LangIdSummaryBarChart
                      summaries={summaries}
                      valueOf={(s) => s.mean_elapsed_ms}
                      formatValue={(v) => `${v.toFixed(1)} мс`}
                      ariaLabel="Среднее время по методам"
                    />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between gap-3">
                  <CardTitle>Результаты по документам</CardTitle>
                  <div className="flex gap-2">
                    <Button type="button" variant="outline" size="sm" onClick={handleExportCsv}>
                      Скачать CSV
                    </Button>
                    <Button type="button" variant="outline" size="sm" onClick={handleExportJson}>
                      Экспорт JSON
                    </Button>
                    <Button type="button" variant="outline" size="sm" onClick={() => window.print()}>
                      Печать
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <LangIdResultsTable documents={testDocuments} resultsByMethod={resultsByMethod} />
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
