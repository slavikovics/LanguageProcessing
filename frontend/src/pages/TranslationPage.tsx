import { HelpCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { getLatestTranslationRunForCollection } from "@/api/client";
import type { TranslationRun } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TranslationDictionaryTab } from "@/components/TranslationDictionaryTab";
import { TranslationDocumentTab } from "@/components/TranslationDocumentTab";
import { TranslationSyntaxTab } from "@/components/TranslationSyntaxTab";
import { TranslationWordListTab } from "@/components/TranslationWordListTab";
import { useCollectionContext } from "@/context/CollectionContext";

export function TranslationPage() {
  const { selectedId } = useCollectionContext();
  const [run, setRun] = useState<TranslationRun | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get("tab") ?? "translate";

  useEffect(() => {
    if (selectedId === null) {
      setRun(null);
      return;
    }
    let cancelled = false;
    getLatestTranslationRunForCollection(selectedId).then((latest) => {
      if (!cancelled) setRun(latest);
    });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  return (
    <div className="flex flex-col gap-6">
      <Card className="relative py-4">
        <Button
          asChild
          variant="ghost"
          size="icon-sm"
          aria-label="Справка о машинном переводе"
          className="absolute top-3 right-3 text-muted-foreground"
        >
          <Link to="/help#translation">
            <HelpCircle className="size-4" />
          </Link>
        </Button>
        <CardHeader>
          <CardTitle>Автоматический машинный перевод текстов</CardTitle>
          <CardDescription>
            Прямой (пословный) перевод английский → французский: каждое слово ищется в двуязычном
            словаре по лемме и части речи и заменяется переводом — частотный список слов с
            грамматической информацией, дерево синтаксического разбора предложения и утилита
            пополнения словаря на случай пробелов.
          </CardDescription>
        </CardHeader>
      </Card>

      <Tabs
        value={activeTab}
        onValueChange={(value) => setSearchParams({ tab: value }, { replace: true })}
      >
        <TabsList>
          <TabsTrigger value="translate">Перевод</TabsTrigger>
          <TabsTrigger value="words">Слова</TabsTrigger>
          <TabsTrigger value="syntax">Синтаксис</TabsTrigger>
          <TabsTrigger value="dictionary">Словарь</TabsTrigger>
        </TabsList>

        <TabsContent value="translate" className="pt-4">
          <TranslationDocumentTab collectionId={selectedId} run={run} onRunCreated={setRun} />
        </TabsContent>

        <TabsContent value="words" className="pt-4 data-[state=inactive]:hidden" forceMount>
          <TranslationWordListTab run={run} />
        </TabsContent>

        <TabsContent value="syntax" className="pt-4 data-[state=inactive]:hidden" forceMount>
          <TranslationSyntaxTab run={run} />
        </TabsContent>

        <TabsContent value="dictionary" className="pt-4 data-[state=inactive]:hidden" forceMount>
          <TranslationDictionaryTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
