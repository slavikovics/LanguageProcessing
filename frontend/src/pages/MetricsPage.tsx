import { LangIdMetricsSection } from "@/components/LangIdMetricsSection";
import { SearchMetricsSection } from "@/components/SearchMetricsSection";
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
            раздел ниже: качество поиска и качество определения языка. В следующих лабораторных
            здесь появятся и другие разделы (например, качество реферирования).
          </CardDescription>
        </CardHeader>
      </Card>

      <SearchMetricsSection collectionId={selectedId} />
      <LangIdMetricsSection collectionId={selectedId} />
    </div>
  );
}
