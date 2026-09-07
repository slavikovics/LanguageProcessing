import { ModelSwatch } from "@/components/ModelSwatch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { colorForModel } from "@/lib/modelColors";
import { LANG_ID_METHOD_LABELS, type LangIdRunSummary } from "../api/types";

const METRICS: {
  key: "accuracy" | "precision" | "recall" | "f1" | "mean_elapsed_ms" | "documents_evaluated";
  label: string;
  format: (v: number) => string;
}[] = [
  { key: "accuracy", label: "Accuracy", format: (v) => `${(v * 100).toFixed(1)}%` },
  { key: "precision", label: "Precision (macro)", format: (v) => `${(v * 100).toFixed(1)}%` },
  { key: "recall", label: "Recall (macro)", format: (v) => `${(v * 100).toFixed(1)}%` },
  { key: "f1", label: "F1 (macro)", format: (v) => `${(v * 100).toFixed(1)}%` },
  { key: "mean_elapsed_ms", label: "Среднее время классификации", format: (v) => `${v.toFixed(2)} мс` },
  { key: "documents_evaluated", label: "Документов протестировано", format: (v) => `${v}` },
];

export function LangIdMethodComparisonTable({ summaries }: { summaries: LangIdRunSummary[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Метрика</TableHead>
          {summaries.map((s) => (
            <TableHead key={s.method} className="text-right">
              <ModelSwatch label={LANG_ID_METHOD_LABELS[s.method]} color={colorForModel(s.method)} />
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {METRICS.map((metric) => (
          <TableRow key={metric.key}>
            <TableCell>{metric.label}</TableCell>
            {summaries.map((s) => (
              <TableCell key={s.method} className="text-right font-medium tabular-nums">
                {metric.format(s[metric.key])}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
