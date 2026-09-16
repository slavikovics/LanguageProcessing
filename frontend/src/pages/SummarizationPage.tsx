import { HelpCircle } from "lucide-react";
import { Link } from "react-router-dom";

import { SummarizationDocumentTab } from "@/components/SummarizationDocumentTab";
import { SummarizationTestingTab } from "@/components/SummarizationTestingTab";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCollectionContext } from "@/context/CollectionContext";

export function SummarizationPage() {
  const { selected, selectedId } = useCollectionContext();

  if (selectedId === null || !selected) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Нет выбранной коллекции</CardTitle>
          <CardDescription>
            Выберите или создайте коллекцию через переключатель вверху страницы — реферат
            строится для документов конкретной коллекции.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Card className="relative py-4">
        <Button
          asChild
          variant="ghost"
          size="icon-sm"
          aria-label="Справка о реферировании"
          className="absolute top-3 right-3 text-muted-foreground"
        >
          <Link to="/help#summarization">
            <HelpCircle className="size-4" />
          </Link>
        </Button>
        <CardHeader>
          <CardTitle>Автоматическое реферирование документов</CardTitle>
          <CardDescription>
            Три метода извлечения ключевых предложений — модифицированный TF-IDF с учётом позиции
            предложения, графовый TextRank и косинусная близость эмбеддингов (к центроиду документа
            или к вашему запросу) — постройте и сравните реферат и иерархический список ключевых
            слов, при желании перефразируйте текст с помощью LLM.
          </CardDescription>
        </CardHeader>
      </Card>

      <Tabs defaultValue="document">
        <TabsList>
          <TabsTrigger value="document">Реферат документа</TabsTrigger>
          <TabsTrigger value="testing">Тестирование</TabsTrigger>
        </TabsList>

        <TabsContent value="document" className="pt-4">
          <SummarizationDocumentTab collectionId={selectedId} />
        </TabsContent>

        {}
        <TabsContent value="testing" className="pt-4 data-[state=inactive]:hidden" forceMount>
          <SummarizationTestingTab collectionId={selectedId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
