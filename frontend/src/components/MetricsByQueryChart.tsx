import { useState } from "react";
import { QueryMetricBarChart, type QuerySeries } from "@/components/QueryMetricBarChart";
import { QueryTextDialog } from "@/components/QueryTextDialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { QueryMetrics } from "../api/types";

const RANKING_METRICS: { value: string; key: keyof QueryMetrics; label: string }[] = [
  { value: "ap", key: "average_precision", label: "AP" },
  { value: "r-prec", key: "r_precision", label: "R-Precision" },
  { value: "p5", key: "precision_at_5", label: "P@5" },
  { value: "p10", key: "precision_at_10", label: "P@10" },
  { value: "r5", key: "recall_at_5", label: "R@5" },
  { value: "r10", key: "recall_at_10", label: "R@10" },
  { value: "f1-5", key: "f1_at_5", label: "F1@5" },
  { value: "f1-10", key: "f1_at_10", label: "F1@10" },
];

export function MetricsByQueryChart({ series }: { series: QuerySeries[] }) {
  const [selectedQuery, setSelectedQuery] = useState<string | null>(null);

  return (
    <Tabs defaultValue="ap">
      <TabsList>
        {RANKING_METRICS.map((m) => (
          <TabsTrigger key={m.value} value={m.value}>
            {m.label}
          </TabsTrigger>
        ))}
      </TabsList>
      {}
      <div className="relative">
        {RANKING_METRICS.map((m) => (
          <TabsContent
            key={m.value}
            value={m.value}
            forceMount
            className="data-[state=inactive]:invisible data-[state=inactive]:pointer-events-none data-[state=inactive]:absolute data-[state=inactive]:inset-0"
          >
            <QueryMetricBarChart series={series} metricKey={m.key} onSelectQuery={setSelectedQuery} />
          </TabsContent>
        ))}
      </div>
      <QueryTextDialog query={selectedQuery} onClose={() => setSelectedQuery(null)} />
    </Tabs>
  );
}
