import { Languages, Loader2, Printer, Save } from "lucide-react";
import { useState } from "react";

import { createTranslationRun } from "@/api/client";
import type { DocumentSummary, TranslationMethod, TranslationRun } from "@/api/types";
import { TRANSLATION_METHOD_LABELS } from "@/api/types";
import { DocumentCombobox } from "@/components/DocumentCombobox";
import { SpeakButton } from "@/components/SpeakButton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useReadableText } from "@/context/SpeechModeContext";
import { escapeHtml, openPrintView } from "@/lib/printView";

export function TranslationDocumentTab({
  collectionId,
  method,
  run,
  onRunCreated,
}: {
  collectionId: number | null;
  method: TranslationMethod;
  run: TranslationRun | null;
  onRunCreated: (run: TranslationRun) => void;
}) {
  const [selectedDocument, setSelectedDocument] = useState<DocumentSummary | null>(null);
  const [pastedText, setPastedText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canTranslate = selectedDocument !== null || pastedText.trim().length > 0;
  useReadableText(run?.source_text ?? "");
  useReadableText(run?.translated_text ?? "");

  async function handleTranslate() {
    setLoading(true);
    setError(null);
    try {
      const created = await createTranslationRun({
        documentId: selectedDocument?.id,
        text: selectedDocument ? undefined : pastedText,
        collectionId: selectedDocument ? undefined : (collectionId ?? undefined),
        method,
      });
      onRunCreated(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  function handleSaveToFile() {
    if (!run) return;
    const lines = [
      `Направление перевода: ${run.source_lang.toUpperCase()} → ${run.target_lang.toUpperCase()}`,
      `Слов во входном тексте: ${run.word_count}`,
      `Переведено слов: ${run.translated_word_count}`,
      "",
      "--- Исходный текст ---",
      run.source_text,
      "",
      "--- Перевод ---",
      run.translated_text,
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `translation-${run.id}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function handlePrint() {
    if (!run) return;
    openPrintView(
      "Машинный перевод",
      `
        <h1>Машинный перевод</h1>
        <p class="meta">${escapeHtml(run.source_lang.toUpperCase())} → ${escapeHtml(run.target_lang.toUpperCase())} ·
        слов: ${run.word_count}, переведено: ${run.translated_word_count}</p>
        <h2>Исходный текст</h2>
        <p>${escapeHtml(run.source_text)}</p>
        <h2>Перевод</h2>
        <p>${escapeHtml(run.translated_text)}</p>
      `,
    );
  }

  const translatedPercent =
    run && run.word_count > 0 ? Math.round((run.translated_word_count / run.word_count) * 100) : 0;

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-col gap-4 py-4">
          {collectionId !== null && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="translation-document">Документ из коллекции (необязательно)</Label>
              <DocumentCombobox
                id="translation-document"
                collectionId={collectionId}
                value={selectedDocument}
                onChange={setSelectedDocument}
                placeholder="Выбрать документ вместо вставки текста"
              />
            </div>
          )}

          {!selectedDocument && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="translation-text">Текст на входном языке</Label>
              <Textarea
                id="translation-text"
                value={pastedText}
                onChange={(event) => setPastedText(event.target.value)}
                placeholder="Вставьте текст научной статьи по медицине или критику произведения изобразительного искусства на английском…"
                className="h-40"
              />
            </div>
          )}

          <div className="flex flex-wrap items-center justify-center gap-2">
            <Button type="button" onClick={handleTranslate} disabled={!canTranslate || loading}>
              {loading ? <Loader2 className="size-4 animate-spin" /> : <Languages className="size-4" />}
              {loading ? "Перевод…" : "Перевести (EN → FR)"}
            </Button>
            {run && (
              <>
                <Button type="button" variant="outline" onClick={handleSaveToFile}>
                  <Save className="size-4" />
                  Сохранить в файл
                </Button>
                <Button type="button" variant="outline" onClick={handlePrint}>
                  <Printer className="size-4" />
                  Печать
                </Button>
              </>
            )}
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>

      {run && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader className="flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-1.5">
                <CardTitle className="text-base">Исходный текст ({run.source_lang.toUpperCase()})</CardTitle>
                <SpeakButton text={run.source_text} size="icon-sm" variant="ghost" />
              </div>
              <span className="text-sm whitespace-nowrap text-muted-foreground">
                Слов: <span className="font-medium text-foreground">{run.word_count}</span>
              </span>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm break-words">{run.source_text}</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-1.5">
                <CardTitle className="text-base">Перевод ({run.target_lang.toUpperCase()})</CardTitle>
                <SpeakButton text={run.translated_text} size="icon-sm" variant="ghost" />
                <Badge variant="secondary">{TRANSLATION_METHOD_LABELS[run.method]}</Badge>
              </div>
              <span className="text-sm whitespace-nowrap text-muted-foreground">
                Переведено: <span className="font-medium text-foreground">{run.translated_word_count}</span>{" "}
                ({translatedPercent}%)
              </span>
            </CardHeader>
            <CardContent>
              {run.diff_segments && run.diff_segments.length > 0 ? (
                <div className="flex flex-col gap-2">
                  <p className="text-xs text-muted-foreground">
                    <mark className="rounded-sm bg-amber-200 px-0.5 text-foreground dark:bg-amber-400/40">
                      Выделено
                    </mark>{" "}
                    — отличается от прямого перевода: здесь сработало правило трансфера
                  </p>
                  <p className="whitespace-pre-wrap text-sm break-words">
                    {run.diff_segments.map((segment, index) =>
                      segment.changed ? (
                        <mark
                          key={index}
                          className="rounded-sm bg-amber-200 px-0.5 text-foreground dark:bg-amber-400/40"
                          title="Отличается от прямого перевода: сработало правило трансфера"
                        >
                          {segment.text}
                        </mark>
                      ) : (
                        <span key={index}>{segment.text}</span>
                      ),
                    )}
                  </p>
                </div>
              ) : (
                <p className="whitespace-pre-wrap text-sm break-words">{run.translated_text}</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
