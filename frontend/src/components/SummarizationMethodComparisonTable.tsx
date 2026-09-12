import { SUMMARIZATION_METHOD_LABELS, type SummarizationRunSummary } from "@/api/types";
import { ModelSwatch } from "@/components/ModelSwatch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { colorForModel } from "@/lib/modelColors";

const METRICS: {
  key: "mean_elapsed_ms" | "mean_compression_ratio" | "mean_sentence_count" | "documents_summarized";
  label: string;
  format: (v: number) => string;
}[] = [
  { key: "mean_elapsed_ms", label: "Среднее время реферирования", format: (v) => `${v.toFixed(2)} мс` },
  { key: "mean_compression_ratio", label: "Средняя степень сжатия", format: (v) => `${(v * 100).toFixed(1)}%` },
  { key: "mean_sentence_count", label: "Среднее число предложений в реферате", format: (v) => v.toFixed(1) },
  { key: "documents_summarized", label: "Документов обработано", format: (v) => `${v}` },
];

export function SummarizationMethodComparisonTable({
  summaries,
}: {
  summaries: SummarizationRunSummary[];
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Метрика</TableHead>
          {summaries.map((s) => (
            <TableHead key={s.method} className="text-right">
              <ModelSwatch label={SUMMARIZATION_METHOD_LABELS[s.method]} color={colorForModel(s.method)} />
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
