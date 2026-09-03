import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function SearchPage() {
  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Поиск</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Векторный поиск (TF-IDF + косинусная мера) будет доступен здесь после реализации
            индексации и поискового движка — см. этап 4 в docs/PROJECT_PLAN.md.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
