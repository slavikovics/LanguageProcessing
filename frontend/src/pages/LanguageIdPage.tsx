import { HelpCircle } from "lucide-react";
import { Link } from "react-router-dom";

import { AdHocClassifyPanel } from "@/components/AdHocClassifyPanel";
import { LangIdLabelingTab } from "@/components/LangIdLabelingTab";
import { LangIdProfilesTab } from "@/components/LangIdProfilesTab";
import { LangIdTestingTab } from "@/components/LangIdTestingTab";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCollectionContext } from "@/context/CollectionContext";

export function LanguageIdPage() {
  const { selected, selectedId } = useCollectionContext();

  if (selectedId === null || !selected) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Нет выбранной коллекции</CardTitle>
          <CardDescription>
            Выберите или создайте коллекцию через переключатель вверху страницы — язык
            определяется для документов конкретной коллекции.
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
          aria-label="Справка об определении языка"
          className="absolute top-3 right-3 text-muted-foreground"
        >
          <Link to="/help#lang-id">
            <HelpCircle className="size-4" />
          </Link>
        </Button>
        <CardHeader>
          <CardTitle>Определение языка текста</CardTitle>
          <CardDescription>
            Методы частотных слов, алфавитный и нейросетевой — разметьте документы, постройте
            профили языков, затем сравните методы на тестовой выборке.
          </CardDescription>
        </CardHeader>
      </Card>

      <Tabs defaultValue="labeling">
        <TabsList>
          <TabsTrigger value="labeling">Разметка</TabsTrigger>
          <TabsTrigger value="profiles">Профили</TabsTrigger>
          <TabsTrigger value="adhoc">Ручная проверка</TabsTrigger>
          <TabsTrigger value="testing">Тестирование</TabsTrigger>
        </TabsList>

        <TabsContent value="labeling" className="pt-4">
          <LangIdLabelingTab collectionId={selectedId} />
        </TabsContent>

        <TabsContent value="profiles" className="pt-4">
          <LangIdProfilesTab />
        </TabsContent>

        <TabsContent value="adhoc" className="pt-4">
          <AdHocClassifyPanel />
        </TabsContent>

        {}
        <TabsContent value="testing" className="pt-4 data-[state=inactive]:hidden" forceMount>
          <LangIdTestingTab collectionId={selectedId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
