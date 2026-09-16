import { Loader2, Sparkles } from "lucide-react";
import { useState } from "react";

import { polishSummary } from "@/api/client";
import { SUMMARIZATION_METHOD_LABELS, type SummaryOutcome } from "@/api/types";
import { MarkdownContent } from "@/components/markdown";
import { ModelSwatch } from "@/components/ModelSwatch";
import { SpeakButton } from "@/components/SpeakButton";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useReadableText } from "@/context/SpeechModeContext";
import { colorForModel } from "@/lib/modelColors";

export function SummarizationResultCard({
  outcome,
  summaryId,
  onPolished,
}: {
  outcome: SummaryOutcome;
  summaryId: number | null;
  onPolished?: (result: { markdown: string; model: string }) => void;
}) {
  const [polished, setPolished] = useState<string | null>(null);
  const [polishedModel, setPolishedModel] = useState<string | null>(null);
  const [polishing, setPolishing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const summaryText = outcome.sentences.map((sentence) => sentence.text).join(" ");
  // Registers raw summary first so "read this" follows top-to-bottom page order.
  useReadableText(summaryText);
  useReadableText(!polishing && polished ? polished : "");

  async function handlePolish() {
    if (summaryId === null) return;
    setPolishing(true);
    setError(null);
    try {
      const result = await polishSummary(summaryId);
      setPolished(result.polished_markdown);
      setPolishedModel(result.model);
      onPolished?.({ markdown: result.polished_markdown, model: result.model });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setPolishing(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card className="flex flex-col">
        <CardHeader className="items-center gap-1.5 text-center">
          <CardTitle>
            <ModelSwatch
              label={SUMMARIZATION_METHOD_LABELS[outcome.method]}
              color={colorForModel(outcome.method)}
            />
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            {outcome.sentences.length} из {outcome.total_sentences} предложений
            {" · "}
            {(outcome.compression_ratio * 100).toFixed(0)}% объёма
            {" · "}
            {outcome.elapsed_ms.toFixed(0)} мс
          </p>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col gap-3">
          <p className="flex-1 text-sm leading-relaxed break-words">{summaryText}</p>

          <div className="flex flex-wrap items-center justify-center gap-2">
            <SpeakButton text={summaryText} size="sm" variant="outline" />
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handlePolish}
              disabled={polishing || summaryId === null}
            >
              {polishing ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Sparkles className="size-3.5" />
              )}
              {polishing ? "Перефразирование…" : "Перефразировать с помощью LLM"}
            </Button>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
        </CardContent>
      </Card>

      {(polishing || polished) && (
        <Card className="flex flex-col">
          <CardHeader className="items-center gap-1.5 text-center">
            <CardTitle>
              <ModelSwatch label={polishedModel ?? "LLM"} color={colorForModel(polishedModel ?? "llm")} />
            </CardTitle>
            <p className="text-xs text-muted-foreground">Перефразированная версия реферата</p>
          </CardHeader>
          <CardContent className="flex flex-1 flex-col gap-3">
            {polishing && (
              <div className="flex flex-1 items-center justify-center py-6 text-muted-foreground">
                <Loader2 className="size-5 animate-spin" />
              </div>
            )}
            {!polishing && polished && (
              <>
                <MarkdownContent content={polished} compact />
                <SpeakButton text={polished} size="sm" variant="outline" className="self-center" />
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
