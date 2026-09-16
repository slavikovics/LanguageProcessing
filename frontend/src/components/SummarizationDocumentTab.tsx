import { FileText, Loader2, Printer, Save } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { listDocumentSummaries, listDocuments, summarizeDocument } from "@/api/client";
import {
  SUMMARIZATION_METHODS,
  SUMMARIZATION_METHOD_LABELS,
  type DocumentSummary,
  type KeywordGroup,
  type SummarizationMethod,
  type SummaryOutcome,
} from "@/api/types";
import { DocumentCombobox } from "@/components/DocumentCombobox";
import { SummarizationKeywordTree } from "@/components/SummarizationKeywordTree";
import { SummarizationResultCard } from "@/components/SummarizationResultCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { escapeHtml, markdownToPrintHtml, openPrintView } from "@/lib/printView";

const DEFAULT_SENTENCE_COUNT = 10;
const DEFAULT_KEYWORD_COUNT = 15;
const ALL_METHODS = "all" as const;
type MethodSelection = SummarizationMethod | typeof ALL_METHODS;

interface PolishedResult {
  markdown: string;
  model: string;
}

export function SummarizationDocumentTab({ collectionId }: { collectionId: number }) {
  const [selectedDocument, setSelectedDocument] = useState<DocumentSummary | null>(null);
  const [method, setMethod] = useState<MethodSelection>(SUMMARIZATION_METHODS[0]);
  const [sentenceCount, setSentenceCount] = useState(DEFAULT_SENTENCE_COUNT);
  const [keywordCount, setKeywordCount] = useState(DEFAULT_KEYWORD_COUNT);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [keywords, setKeywords] = useState<KeywordGroup[]>([]);
  const [outcomes, setOutcomes] = useState<SummaryOutcome[]>([]);
  const [summaryIdByMethod, setSummaryIdByMethod] = useState<Record<string, number | null>>({});
  const [polishedByMethod, setPolishedByMethod] = useState<Record<string, PolishedResult>>({});

  useEffect(() => {
    setSelectedDocument(null);
    void listDocuments(collectionId, { limit: 1 }).then((docs) => {
      setSelectedDocument(docs[0] ?? null);
    });
  }, [collectionId]);

  const handleSummarize = useCallback(async () => {
    const documentId = selectedDocument?.id;
    if (documentId === undefined) return;
    setLoading(true);
    setError(null);
    setKeywords([]);
    setOutcomes([]);
    setPolishedByMethod({});
    try {
      const methods = method === ALL_METHODS ? [...SUMMARIZATION_METHODS] : [method];
      const response = await summarizeDocument(documentId, {
        methods,
        sentenceCount,
        keywordCount,
        query: query.trim() || undefined,
      });
      setKeywords(response.keywords);
      setOutcomes(response.results);

      const persisted = await listDocumentSummaries(documentId);
      const latestByMethod: Record<string, number | null> = {};
      for (const outcome of response.results) {
        const match = persisted.find((row) => row.method === outcome.method);
        latestByMethod[outcome.method] = match?.id ?? null;
      }
      setSummaryIdByMethod(latestByMethod);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [selectedDocument, method, sentenceCount, keywordCount, query]);

  function keywordHierarchyLines(groups: KeywordGroup[]): string[] {
    return groups.flatMap((group) => [group.term, ...group.children.map((child) => `  ${child}`)]);
  }

  function handleSaveToFile() {
    const lines = [
      `Документ: ${selectedDocument?.title ?? ""}`,
      selectedDocument?.url ? `Ссылка: ${selectedDocument.url}` : null,
      "",
      "Ключевые слова:",
      ...keywordHierarchyLines(keywords),
      "",
      ...outcomes.flatMap((outcome) => [
        `--- ${outcome.method} ---`,
        outcome.sentences.map((sentence) => sentence.text).join(" "),
        "",
      ]),
    ].filter((line): line is string => line !== null);

    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `summary-${selectedDocument?.id ?? "document"}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function keywordTreeHtml(groups: KeywordGroup[]): string {
    if (groups.length === 0) return "<p>—</p>";
    return `<ul class="keyword-tree">${groups
      .map((group) => {
        const children = group.children.length
          ? `<ul>${group.children.map((child) => `<li>${escapeHtml(child)}</li>`).join("")}</ul>`
          : "";
        return `<li>${escapeHtml(group.term)}${children}</li>`;
      })
      .join("")}</ul>`;
  }

  function handlePrint() {
    const title = selectedDocument?.title ?? "Реферат документа";
    const outcomesHtml = outcomes
      .map((outcome) => {
        const polished = polishedByMethod[outcome.method];
        const polishedHtml = polished
          ? `
              <h3>Перефразировано (${escapeHtml(polished.model)})</h3>
              ${markdownToPrintHtml(polished.markdown)}
            `
          : "";
        return `
          <h2>${escapeHtml(SUMMARIZATION_METHOD_LABELS[outcome.method])}</h2>
          <p>${escapeHtml(outcome.sentences.map((sentence) => sentence.text).join(" "))}</p>
          ${polishedHtml}
        `;
      })
      .join("");

    openPrintView(
      title,
      `
        <h1>${escapeHtml(title)}</h1>
        ${selectedDocument?.url ? `<p class="meta">${escapeHtml(selectedDocument.url)}</p>` : ""}
        <h2>Ключевые слова</h2>
        ${keywordTreeHtml(keywords)}
        ${outcomesHtml}
      `,
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-col gap-4 py-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:flex-wrap">
            <div className="flex min-w-64 flex-1 flex-col gap-1.5">
              <Label htmlFor="summarization-document">Документ</Label>
              <DocumentCombobox
                id="summarization-document"
                collectionId={collectionId}
                value={selectedDocument}
                onChange={setSelectedDocument}
              />
            </div>

            <div className="flex min-w-48 flex-col gap-1.5">
              <Label htmlFor="summarization-method">Метод</Label>
              <Select value={method} onValueChange={(value) => setMethod(value as MethodSelection)}>
                <SelectTrigger id="summarization-method" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SUMMARIZATION_METHODS.map((m) => (
                    <SelectItem key={m} value={m}>
                      {SUMMARIZATION_METHOD_LABELS[m]}
                    </SelectItem>
                  ))}
                  <SelectItem value={ALL_METHODS}>Все методы сразу</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="summarization-sentence-count">Предложений в реферате</Label>
              <Input
                id="summarization-sentence-count"
                type="number"
                min={1}
                max={50}
                value={sentenceCount}
                onChange={(event) => setSentenceCount(Number(event.target.value) || 1)}
                className="w-32"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="summarization-keyword-count">Слов в списке ключевых слов</Label>
              <Input
                id="summarization-keyword-count"
                type="number"
                min={1}
                max={100}
                value={keywordCount}
                onChange={(event) => setKeywordCount(Number(event.target.value) || 1)}
                className="w-32"
              />
            </div>

          </div>

          {(method === "embeddings" || method === ALL_METHODS) && (
            <div className="flex flex-col gap-1.5 sm:max-w-md">
              <Label htmlFor="summarization-query">Запрос (эмбеддинги, необязательно)</Label>
              <Input
                id="summarization-query"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Оставьте пустым для реферата по центроиду документа"
              />
            </div>
          )}

          <div className="flex flex-wrap items-end justify-between gap-2">
            {selectedDocument?.url ? (
              <p className="text-xs text-muted-foreground">
                Исходный документ:{" "}
                <a
                  href={selectedDocument.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary underline-offset-2 hover:underline"
                >
                  {selectedDocument.url}
                </a>
              </p>
            ) : (
              <span />
            )}

            <div className="flex flex-wrap gap-2">
              {outcomes.length > 0 && (
                <>
                  <Button type="button" variant="outline" size="sm" onClick={handleSaveToFile}>
                    <Save className="size-3.5" />
                    Сохранить в файл
                  </Button>
                  <Button type="button" variant="outline" size="sm" onClick={handlePrint}>
                    <Printer className="size-3.5" />
                    Печать
                  </Button>
                </>
              )}
              <Button type="button" onClick={handleSummarize} disabled={selectedDocument === null || loading}>
                {loading ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <FileText className="size-4" />
                )}
                {loading ? "Построение…" : "Построить реферат"}
              </Button>
            </div>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>

      {outcomes.length > 0 && (
        <>
          <Card>
            <CardContent className="flex min-w-0 items-center gap-1.5 py-4">
              <h3 className="shrink-0 text-sm font-medium">Ключевые слова:</h3>
              <p className="min-w-0 truncate text-sm text-muted-foreground">
                {keywords.map((group) => group.term).join(", ")}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="text-center">
              <CardTitle>Иерархический список ключевых слов</CardTitle>
            </CardHeader>
            <CardContent>
              <SummarizationKeywordTree groups={keywords} />
            </CardContent>
          </Card>

          <div className="flex flex-col gap-4">
            {outcomes.map((outcome) => (
              <SummarizationResultCard
                key={outcome.method}
                outcome={outcome}
                summaryId={summaryIdByMethod[outcome.method] ?? null}
                onPolished={(result) =>
                  setPolishedByMethod((prev) => ({ ...prev, [outcome.method]: result }))
                }
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
