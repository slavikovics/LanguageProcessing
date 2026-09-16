import { LangIdMetricsSection } from "@/components/LangIdMetricsSection";
import { SearchMetricsSection } from "@/components/SearchMetricsSection";
import { SummarizationMetricsSection } from "@/components/SummarizationMetricsSection";
import { TranslationMetricsSection } from "@/components/TranslationMetricsSection";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useCollectionContext } from "@/context/CollectionContext";

export function MetricsPage() {
  const { selectedId } = useCollectionContext();

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Метрики качества</CardTitle>
          <CardDescription>
            Оценка качества работы системы по каждой из решаемых задач — у каждой задачи свой
            раздел ниже: качество поиска, качество определения языка, качество реферирования и
            качество машинного перевода.
          </CardDescription>
        </CardHeader>
      </Card>

      <SearchMetricsSection collectionId={selectedId} />
      <LangIdMetricsSection collectionId={selectedId} />
      <SummarizationMetricsSection collectionId={selectedId} />
      <TranslationMetricsSection collectionId={selectedId} />
    </div>
  );
}
