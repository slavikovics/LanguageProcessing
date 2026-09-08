import { BrainCircuit } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { trainNeuralProfile } from "../api/client";
import type { LangIdProfile } from "../api/types";
import { useLangIdTrainingProgress } from "../hooks/useLangIdTrainingProgress";

import { LossCurveChart, type LossPoint } from "@/components/LossCurveChart";
import { ProgressBar } from "@/components/ProgressBar";
import { Button } from "@/components/ui/button";

export function NeuralTrainingPanel({
  profile,
  onTrained,
}: {
  profile: LangIdProfile | undefined;
  onTrained: () => void;
}) {
  const [jobId, setJobId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lossHistory, setLossHistory] = useState<LossPoint[]>([]);
  const { progress: job } = useLangIdTrainingProgress(jobId);
  const notifiedRef = useRef(false);

  useEffect(() => {
    if (!job) return;
    setLossHistory((history) => {
      if (job.current_loss === null) return history;
      if (history.length > 0 && history[history.length - 1].epoch === job.epochs_completed) {
        return history;
      }
      return [...history, { epoch: job.epochs_completed, loss: job.current_loss }];
    });
    if ((job.status === "completed" || job.status === "failed") && !notifiedRef.current) {
      notifiedRef.current = true;
      onTrained();
    }
  }, [job]);

  async function handleTrain() {
    setError(null);
    setLossHistory([]);
    notifiedRef.current = false;
    try {
      const created = await trainNeuralProfile();
      setJobId(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const isTraining = job !== null && (job.status === "pending" || job.status === "running");

  return (
    <div className="flex flex-col gap-3 rounded-md border p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <BrainCircuit className="size-4 text-muted-foreground" />
          <span className="text-sm font-medium">Нейросетевой метод</span>
        </div>
        <Button type="button" size="sm" onClick={handleTrain} disabled={isTraining}>
          {isTraining ? "Обучение…" : "Обучить"}
        </Button>
      </div>

      {profile && !isTraining && (
        <p className="text-xs text-muted-foreground">
          Обучено на {profile.source_document_count} документах ·{" "}
          {new Date(profile.built_at).toLocaleString()}
        </p>
      )}
      {!profile && !isTraining && (
        <p className="text-xs text-muted-foreground">Классификатор ещё не обучен.</p>
      )}
      {error && <p className="text-xs text-destructive">{error}</p>}

      {job && (
        <div className="flex flex-col gap-2">
          <ProgressBar value={job.epochs_completed} max={Math.max(job.epochs_total, 1)} complete={job.status === "completed"} />
          {job.current_loss !== null && job.current_train_accuracy !== null && (
            <p className="text-xs text-muted-foreground">
              Эпоха {job.epochs_completed} из {job.epochs_total} · loss{" "}
              {job.current_loss.toFixed(4)} · точность на обучении{" "}
              {(job.current_train_accuracy * 100).toFixed(1)}%
            </p>
          )}
          {job.status === "failed" && (
            <p className="text-xs text-destructive">Ошибка обучения: {job.error_message}</p>
          )}
          {lossHistory.length > 1 && <LossCurveChart points={lossHistory} />}
        </div>
      )}
    </div>
  );
}
