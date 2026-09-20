import { HelpCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { getLatestTranslationRunForCollection } from "@/api/client";
import type { TranslationMethod, TranslationRun } from "@/api/types";
import { TRANSLATION_METHOD_LABELS } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TranslationDictionaryTab } from "@/components/TranslationDictionaryTab";
import { TranslationDocumentTab } from "@/components/TranslationDocumentTab";
import { TranslationSyntaxTab } from "@/components/TranslationSyntaxTab";
import { TranslationTestingTab } from "@/components/TranslationTestingTab";
import { TranslationWordListTab } from "@/components/TranslationWordListTab";
import { useCollectionContext } from "@/context/CollectionContext";

const TRANSLATION_METHODS: TranslationMethod[] = ["direct", "transfer", "neural"];

export function TranslationPage() {
  const { selectedId } = useCollectionContext();
  const [method, setMethod] = useState<TranslationMethod>("direct");
  const [run, setRun] = useState<TranslationRun | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get("tab") ?? "translate";

  useEffect(() => {
    if (selectedId === null) {
      setRun(null);
      return;
    }
    let cancelled = false;
    getLatestTranslationRunForCollection(selectedId, method).then((latest) => {
      if (!cancelled) setRun(latest);
    });
    return () => {
      cancelled = true;
    };
  }, [selectedId, method]);

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
        <CardHeader className="flex flex-col gap-3">
          <div>
            <CardTitle>Автоматический машинный перевод текстов</CardTitle>
            <CardDescription>
              Английский → французский. Прямой метод заменяет каждое слово переводом из словаря по
              лемме и части речи. Трансферный метод дополнительно перестраивает дерево
              синтаксического разбора (порядок прилагательных, отрицание «ne … pas», слияние
              предлогов с артиклем). Нейросетевой метод переводит локальной моделью MarianMT без
              словаря — частотный список слов и покрытие словаря показываются и для него, но
              относятся только к исходному тексту, а не к качеству нейроперевода.
            </CardDescription>
          </div>
          <div className="flex gap-1.5 self-start rounded-md border p-1">
            {TRANSLATION_METHODS.map((option) => (
              <Button
                key={option}
                type="button"
                size="sm"
                variant={method === option ? "default" : "ghost"}
                onClick={() => setMethod(option)}
              >
                {TRANSLATION_METHOD_LABELS[option]}
              </Button>
            ))}
          </div>
        </CardHeader>
      </Card>

      <Tabs
        value={activeTab}
        onValueChange={(value) => setSearchParams({ tab: value }, { replace: true })}
      >
        <TabsList>
          <TabsTrigger value="translate">Перевод</TabsTrigger>
          <TabsTrigger value="testing">Тестирование</TabsTrigger>
          <TabsTrigger value="words">Слова</TabsTrigger>
          <TabsTrigger value="syntax">Синтаксис</TabsTrigger>
          <TabsTrigger value="dictionary">Словарь</TabsTrigger>
        </TabsList>

        <TabsContent value="translate" className="pt-4">
          <TranslationDocumentTab
            collectionId={selectedId}
            method={method}
            run={run}
            onRunCreated={setRun}
          />
        </TabsContent>

        <TabsContent value="testing" className="pt-4 data-[state=inactive]:hidden" forceMount>
          <TranslationTestingTab collectionId={selectedId} method={method} />
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
