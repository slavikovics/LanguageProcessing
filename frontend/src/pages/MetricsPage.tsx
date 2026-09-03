import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function MetricsPage() {
  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Метрики качества</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Таблицы и графики по метрикам ROMIP (Precision/Recall, MAP, R-Precision,
            11-точечная кривая) появятся здесь после сборки тестовой коллекции с разметкой
            релевантности — см. этап 5 в docs/PROJECT_PLAN.md.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
