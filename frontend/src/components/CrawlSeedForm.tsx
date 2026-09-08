import { Check, FileStack, Globe, Layers, Link2, Lock, Plus, X } from "lucide-react";
import { useEffect, useState } from "react";
import { createCrawlSeed, updateCrawlSeed } from "../api/client";
import type { CrawlSeed } from "../api/types";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { clampNumberInput } from "@/lib/utils";

const QUICK_LANGUAGES = ["en", "fr"];
const DEFAULT_LANGUAGE = "en";
const DEFAULT_MAX_DOCUMENTS = 20;
const DEFAULT_MAX_DEPTH = 1;

export function CrawlSeedForm({
  collectionId,
  editingSeed,
  onCancelEdit,
  onSaved,
}: {
  collectionId: number | null;
  editingSeed: CrawlSeed | null;
  onCancelEdit: () => void;
  onSaved: () => void;
}) {
  const [urlDraft, setUrlDraft] = useState("");
  const [maxDocuments, setMaxDocuments] = useState<number | "">(DEFAULT_MAX_DOCUMENTS);
  const [maxDepth, setMaxDepth] = useState<number | "">(DEFAULT_MAX_DEPTH);
  const [sameDomainOnly, setSameDomainOnly] = useState(false);
  const [language, setLanguage] = useState(DEFAULT_LANGUAGE);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function resetFields() {
    setUrlDraft("");
    setMaxDocuments(DEFAULT_MAX_DOCUMENTS);
    setMaxDepth(DEFAULT_MAX_DEPTH);
    setSameDomainOnly(false);
    setLanguage(DEFAULT_LANGUAGE);
    setError(null);
  }

  useEffect(() => {
    if (editingSeed === null) {
      resetFields();
      return;
    }
    setUrlDraft(editingSeed.url);
    setMaxDocuments(editingSeed.max_documents);
    setMaxDepth(editingSeed.max_depth);
    setSameDomainOnly(editingSeed.same_domain_only);
    setLanguage(editingSeed.language);
    setError(null);
  }, [editingSeed?.id]);

  async function handleSubmit() {
    if (collectionId === null) return;
    const trimmed = urlDraft.trim();
    if (!trimmed) return;
    setSaving(true);
    setError(null);
    try {
      const input = {
        url: trimmed,
        max_documents: clampNumberInput(maxDocuments, 1, 2000),
        max_depth: clampNumberInput(maxDepth, 0, 5),
        same_domain_only: sameDomainOnly,
        language: (language.trim() || DEFAULT_LANGUAGE).toLowerCase(),
      };
      if (editingSeed !== null) {
        await updateCrawlSeed(editingSeed.id, input);
      } else {
        await createCrawlSeed(collectionId, input);
      }
      onSaved();
      resetFields();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-end gap-2">
        <div className="flex min-w-[16rem] flex-1 flex-col gap-1.5">
          <Label className="flex items-center gap-1.5">
            <Link2 className="size-4 text-muted-foreground" />
            Адрес (URL)
          </Label>
          <div className="flex gap-1.5">
            <Input
              type="url"
              value={urlDraft}
              onChange={(e) => setUrlDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void handleSubmit();
                }
                if (e.key === "Escape" && editingSeed !== null) {
                  onCancelEdit();
                }
              }}
              placeholder="https://example.com/"
            />
            {editingSeed !== null && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={onCancelEdit}
                aria-label="Отменить редактирование"
                className="shrink-0 text-muted-foreground"
              >
                <X className="size-4" />
              </Button>
            )}
          </div>
        </div>

        <div className="flex w-32 flex-col gap-1.5">
          <Label className="flex items-center gap-1.5">
            <FileStack className="size-4 text-muted-foreground" />
            Документов
          </Label>
          <Input
            type="number"
            min={1}
            max={2000}
            value={maxDocuments}
            onChange={(e) => setMaxDocuments(e.target.value === "" ? "" : Number(e.target.value))}
            onBlur={() => setMaxDocuments((v) => clampNumberInput(v, 1, 2000))}
          />
        </div>

        <div className="flex w-28 flex-col gap-1.5">
          <Label className="flex items-center gap-1.5">
            <Layers className="size-4 text-muted-foreground" />
            Глубина
          </Label>
          <Input
            type="number"
            min={0}
            max={5}
            value={maxDepth}
            onChange={(e) => setMaxDepth(e.target.value === "" ? "" : Number(e.target.value))}
            onBlur={() => setMaxDepth((v) => clampNumberInput(v, 0, 5))}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label className="flex items-center gap-1.5">
            <Lock className="size-4 text-muted-foreground" />
            Только этот домен
          </Label>
          <div className="flex h-9 items-center justify-center">
            <Checkbox
              size="lg"
              checked={sameDomainOnly}
              onCheckedChange={(checked) => setSameDomainOnly(checked === true)}
            />
          </div>
        </div>

        <div className="flex flex-col items-center gap-1.5">
          <Label className="flex items-center gap-1.5">
            <Globe className="size-4 text-muted-foreground" />
            Язык
          </Label>
          <div className="flex h-9 items-center gap-1">
            {QUICK_LANGUAGES.map((code) => (
              <Button
                key={code}
                type="button"
                size="sm"
                variant={language === code ? "default" : "outline"}
                onClick={() => setLanguage(code)}
              >
                {code.toUpperCase()}
              </Button>
            ))}
            <Input
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              placeholder="en"
              maxLength={10}
              className="w-16"
              title="Присваивается документам, собранным по этому адресу"
            />
          </div>
        </div>

        <Button
          type="button"
          variant={editingSeed !== null ? "default" : "outline"}
          size="icon"
          onClick={handleSubmit}
          disabled={saving}
          aria-label={editingSeed !== null ? "Сохранить адрес" : "Добавить адрес"}
          className="shrink-0 transition-transform duration-150 hover:scale-105 active:scale-95"
        >
          {editingSeed !== null ? <Check className="size-4" /> : <Plus className="size-4" />}
        </Button>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
