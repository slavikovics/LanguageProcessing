import { Split } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { autoSplitTrainTest, getLabelProgress } from "../api/client";
import type { LabelProgress } from "../api/types";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LanguageLabelBrowser } from "@/components/LanguageLabelBrowser";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col items-center text-center">
      <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{label}</span>
      <span className="text-2xl leading-tight font-semibold tracking-tight tabular-nums">{value}</span>
    </div>
  );
}

export function LangIdLabelingTab({ collectionId }: { collectionId: number }) {
  const [labelProgress, setLabelProgress] = useState<LabelProgress | null>(null);
  const refreshLabelProgress = useCallback(async () => {
    setLabelProgress(await getLabelProgress(collectionId));
  }, [collectionId]);
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
    setAutoSplitting(true);
    setAutoSplitError(null);
    setAutoSplitMessage(null);
    try {
      const result = await autoSplitTrainTest(collectionId);
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

  return (
    <div className="flex flex-col gap-4">
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
                autoSplitting || labelProgress.labeled - labelProgress.train_count - labelProgress.test_count <= 0
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
      <LanguageLabelBrowser key={labelBrowserKey} collectionId={collectionId} onLabeled={refreshLabelProgress} />
    </div>
  );
}
