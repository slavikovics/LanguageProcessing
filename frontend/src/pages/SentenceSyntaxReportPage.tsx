import { ArrowLeft, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getTranslationRunSentences, parseSentence } from "@/api/client";
import type { SyntaxToken } from "@/api/types";
import { SyntaxDependencyGraph } from "@/components/SyntaxDependencyGraph";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getDepLabel, getPosStyle } from "@/lib/posTags";

export function SentenceSyntaxReportPage() {
  const { runId, sentenceIndex } = useParams<{ runId: string; sentenceIndex: string }>();
  const [sentenceText, setSentenceText] = useState<string | null>(null);
  const [tokens, setTokens] = useState<SyntaxToken[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId || sentenceIndex === undefined) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setTokens(null);

    (async () => {
      try {
        const sentences = await getTranslationRunSentences(Number(runId));
        const text = sentences[Number(sentenceIndex)];
        if (text === undefined) {
          throw new Error("предложение не найдено");
        }
        if (cancelled) return;
        setSentenceText(text);
        const result = await parseSentence(text);
        if (cancelled) return;
        setTokens(result);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [runId, sentenceIndex]);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Button asChild variant="ghost" size="sm" className="-ml-2 text-muted-foreground">
          <Link to="/translation?tab=syntax">
            <ArrowLeft className="size-4" />К вкладке «Синтаксис»
          </Link>
        </Button>
        <h1 className="text-xl font-semibold">Синтаксический разбор предложения</h1>
        {sentenceText && <p className="text-muted-foreground italic">«{sentenceText}»</p>}
      </div>

      {loading && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Построение дерева разбора…
        </p>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}

      {tokens && (
        <div className="flex flex-col gap-6">
          <div className="flex w-full flex-col gap-2">
            <h2 className="text-sm font-medium">Дерево синтаксического разбора</h2>
            <SyntaxDependencyGraph tokens={tokens} className="h-[600px] w-full" />
          </div>

          <div className="flex w-full flex-col gap-2">
            <h2 className="text-sm font-medium">Токены</h2>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Слово</TableHead>
                  <TableHead>Лемма</TableHead>
                  <TableHead>POS</TableHead>
                  <TableHead>Роль</TableHead>
                  <TableHead>Главное слово</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tokens.map((token) => {
                  const style = getPosStyle(token.pos);
                  return (
                    <TableRow key={token.position}>
                      <TableCell className="text-center font-medium">{token.text}</TableCell>
                      <TableCell className="text-center text-muted-foreground">{token.lemma}</TableCell>
                      <TableCell className="text-center">
                        <Badge
                          variant="outline"
                          style={{ backgroundColor: style.bg, borderColor: style.border, color: style.text }}
                        >
                          {token.pos}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">{getDepLabel(token.dep)}</TableCell>
                      <TableCell className="text-center text-muted-foreground">
                        {token.head_text ?? "— корень —"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </div>
  );
}
