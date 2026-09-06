import { ChevronDown, Globe, ThumbsUp } from "lucide-react";
import { useState, type ReactNode } from "react";
import { getDocument } from "../api/client";
import type { SearchHit } from "../api/types";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlightSnippet(snippet: string, words: string[]): ReactNode {
  const cleaned = [...new Set(words.filter(Boolean))];
  if (cleaned.length === 0) return snippet;
  const pattern = new RegExp(`\\b(${cleaned.map(escapeRegExp).join("|")})\\b`, "gi");
  const parts = snippet.split(pattern);
  return parts.map((part, i) =>
    cleaned.some((w) => w.toLowerCase() === part.toLowerCase()) ? (
      <mark key={i} className="rounded bg-yellow-200 px-0.5 text-foreground dark:bg-yellow-900/60">
        {part}
      </mark>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

export function ResultCard({
  hit,
  isRelevant,
  judgmentMode,
  submittedWords,
  onToggleRelevant,
}: {
  hit: SearchHit;
  isRelevant: boolean;
  judgmentMode: boolean;
  submittedWords: string[];
  onToggleRelevant: (documentId: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [fullText, setFullText] = useState<string | null>(null);
  const [loadingFull, setLoadingFull] = useState(false);

  async function toggleExpand() {
    if (expanded) {
      setExpanded(false);
      return;
    }
    setExpanded(true);
    if (fullText === null) {
      setLoadingFull(true);
      try {
        const detail = await getDocument(hit.document_id);
        setFullText(detail.clean_text);
      } catch {
        setFullText(hit.snippet);
      } finally {
        setLoadingFull(false);
      }
    }
  }

  return (
    <div className="flex flex-col gap-2.5 rounded-md border p-4 transition-shadow duration-200 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-baseline gap-2">
          <span className="shrink-0 text-sm font-semibold text-muted-foreground">#{hit.rank}</span>
          <span className="min-w-0 truncate font-medium">{hit.title}</span>
        </div>
        <div className="shrink-0 text-right text-xs text-muted-foreground">
          <div>score {hit.score.toFixed(3)}</div>
          <div>{new Date(hit.fetched_at).toLocaleDateString()}</div>
        </div>
      </div>

      {!expanded ? (
        <p className="text-sm leading-relaxed break-words text-muted-foreground">
          {highlightSnippet(hit.snippet, submittedWords)}
        </p>
      ) : (
        <div className="flex flex-col gap-2 duration-200 animate-in fade-in slide-in-from-top-1">
          <ScrollArea className="h-56 rounded-md border bg-muted/20">
            <p className="whitespace-pre-wrap break-words p-3 text-sm leading-relaxed">
              {loadingFull ? "Загрузка…" : highlightSnippet(fullText ?? hit.snippet, submittedWords)}
            </p>
          </ScrollArea>
          {hit.matched_terms.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {hit.matched_terms.map((term) => (
                <Badge key={term} variant="outline">
                  {term}
                </Badge>
              ))}
            </div>
          )}
        </div>
      )}

      <button
        type="button"
        onClick={toggleExpand}
        className="flex w-fit items-center gap-1 text-xs text-primary transition-colors hover:text-primary/70"
      >
        <ChevronDown className={cn("size-3.5 transition-transform duration-200", expanded && "rotate-180")} />
        {expanded ? "Свернуть" : "Показать полностью"}
      </button>

      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
          {hit.url ? (
            <>
              <Globe className="size-3.5 shrink-0" />
              <a
                href={hit.url}
                target="_blank"
                rel="noreferrer"
                className="min-w-0 truncate transition-colors hover:text-primary hover:underline"
              >
                {hit.url}
              </a>
            </>
          ) : (
            <span className="italic text-muted-foreground/70">без источника</span>
          )}
        </div>
        {judgmentMode && (
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={() => onToggleRelevant(hit.document_id)}
            aria-label={isRelevant ? "Убрать отметку «релевантен»" : "Отметить как релевантный"}
            aria-pressed={isRelevant}
            className={cn(
              "shrink-0 transition-all duration-150 hover:scale-110",
              isRelevant && "bg-emerald-600/15 text-emerald-600 dark:text-emerald-400",
            )}
          >
            <ThumbsUp className="size-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
