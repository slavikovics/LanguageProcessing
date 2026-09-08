import { Download, FileJson, FileUp, Globe, Printer, Type } from "lucide-react";
import { useRef, useState } from "react";
import { identifyText, identifyUrl } from "../api/client";
import { LANG_ID_METHOD_LABELS, type IdentificationOutcome } from "../api/types";
import { extractFromHtml } from "../lib/htmlExtraction";
import { downloadCsv, downloadJson } from "../lib/exportResults";

import { ModelSwatch } from "@/components/ModelSwatch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { colorForModel } from "@/lib/modelColors";

function ExportToolbar(
  { source, outcomes }: { source: string; outcomes: IdentificationOutcome[] }
) {
  function handleExportCsv() {
    const rows = outcomes.map((o) => ({
      source,
      method: o.method,
      predicted_language: o.predicted_language,
      distances: JSON.stringify(o.distances),
      elapsed_ms: o.elapsed_ms,
    }));
    downloadCsv("lang-id-adhoc-result.csv", rows);
  }

  function handleExportJson() {
    downloadJson("lang-id-adhoc-result.json", { source, results: outcomes });
  }

  return (
    <div className="flex gap-1.5">
      <Button type="button" variant="ghost" size="sm" onClick={handleExportCsv}>
        <Download className="size-3.5" />
        CSV
      </Button>
      <Button type="button" variant="ghost" size="sm" onClick={handleExportJson}>
        <FileJson className="size-3.5" />
        JSON
      </Button>
      <Button type="button" variant="ghost" size="sm" onClick={() => window.print()}>
        <Printer className="size-3.5" />
        Печать
      </Button>
    </div>
  );
}

function OutcomeList({ outcomes }: { outcomes: IdentificationOutcome[] }) {
  if (outcomes.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">
        Ни один метод пока не готов — постройте профили на вкладке «Профили».
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {outcomes.map((outcome) => (
        <div key={outcome.method} className="flex flex-col gap-1 rounded-md border p-2.5">
          <div className="flex items-center justify-between gap-3">
            <ModelSwatch label={LANG_ID_METHOD_LABELS[outcome.method]} color={colorForModel(outcome.method)} />
            <span className="text-sm font-semibold tabular-nums">{outcome.predicted_language.toUpperCase()}</span>
          </div>
          <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
            {Object.entries(outcome.distances).map(([language, distance]) => (
              <span key={language} className="tabular-nums">
                {language}: {distance.toFixed(3)}
              </span>
            ))}
            <span className="tabular-nums">{outcome.elapsed_ms.toFixed(2)} мс</span>
          </div>
        </div>
      ))}
    </div>
  );
}

export function AdHocClassifyPanel() {
  const [url, setUrl] = useState("");
  const [urlLoading, setUrlLoading] = useState(false);
  const [urlError, setUrlError] = useState<string | null>(null);
  const [urlResults, setUrlResults] = useState<IdentificationOutcome[] | null>(null);

  const [text, setText] = useState("");
  const [textLoading, setTextLoading] = useState(false);
  const [textError, setTextError] = useState<string | null>(null);
  const [textResults, setTextResults] = useState<IdentificationOutcome[] | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleClassifyUrl() {
    if (!url.trim()) return;
    setUrlLoading(true);
    setUrlError(null);
    setUrlResults(null);
    try {
      const response = await identifyUrl(url.trim());
      setUrlResults(response.results);
    } catch (err) {
      setUrlError(err instanceof Error ? err.message : String(err));
    } finally {
      setUrlLoading(false);
    }
  }

  async function handleClassifyText() {
    if (!text.trim()) return;
    setTextLoading(true);
    setTextError(null);
    setTextResults(null);
    try {
      const response = await identifyText(text);
      setTextResults(response.results);
    } catch (err) {
      setTextError(err instanceof Error ? err.message : String(err));
    } finally {
      setTextLoading(false);
    }
  }

  async function handleHtmlFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const html = await file.text();
    const { text: extracted } = extractFromHtml(html);
    setText(extracted);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 rounded-md border p-4">
        <div className="flex items-center gap-2">
          <Globe className="size-4 text-muted-foreground" />
          <span className="text-sm font-medium">По адресу страницы</span>
        </div>
        <div className="flex gap-2">
          <Input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/article"
          />
          <Button type="button" onClick={handleClassifyUrl} disabled={urlLoading || !url.trim()}>
            {urlLoading ? "Загрузка…" : "Определить"}
          </Button>
        </div>
        {urlError && <p className="text-xs text-destructive">{urlError}</p>}
        {urlResults && urlResults.length > 0 && (
          <div className="flex justify-end">
            <ExportToolbar source={url.trim()} outcomes={urlResults} />
          </div>
        )}
        {urlResults && <OutcomeList outcomes={urlResults} />}
      </div>

      <div className="flex flex-col gap-3 rounded-md border p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Type className="size-4 text-muted-foreground" />
            <span className="text-sm font-medium">По тексту</span>
          </div>
          <Button type="button" variant="ghost" size="sm" onClick={() => fileInputRef.current?.click()}>
            <FileUp className="size-3.5" />
            Загрузить HTML-файл
          </Button>
          <input ref={fileInputRef} type="file" accept=".html,.htm,text/html" className="hidden" onChange={handleHtmlFile} />
        </div>
        <div className="grid gap-1.5">
          <Label className="sr-only">Текст для классификации</Label>
          <Textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="h-32"
            placeholder="Вставьте текст или загрузите HTML-файл…"
          />
        </div>
        <Button type="button" onClick={handleClassifyText} disabled={textLoading || !text.trim()} className="self-end">
          {textLoading ? "Обработка…" : "Определить"}
        </Button>
        {textError && <p className="text-xs text-destructive">{textError}</p>}
        {textResults && textResults.length > 0 && (
          <div className="flex justify-end">
            <ExportToolbar
              source={text.trim().length > 200 ? `${text.trim().slice(0, 200)}…` : text.trim()}
              outcomes={textResults}
            />
          </div>
        )}
        {textResults && <OutcomeList outcomes={textResults} />}
      </div>
    </div>
  );
}
