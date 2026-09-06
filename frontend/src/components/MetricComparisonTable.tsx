import { ModelSwatch } from "@/components/ModelSwatch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { colorForModel } from "@/lib/modelColors";
import type { CollectionMetricsSummary } from "../api/types";

export function MetricComparisonTable({
  summaries,
  metrics,
}: {
  summaries: CollectionMetricsSummary[];
  metrics: { key: keyof CollectionMetricsSummary; label: string; hint?: string }[];
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Метрика</TableHead>
          {summaries.map((s) => (
            <TableHead key={s.model} className="text-right">
              <ModelSwatch label={s.model_label} color={colorForModel(s.model)} />
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {metrics.map((m) => (
          <TableRow key={m.key}>
            <TableCell>
              <div className="flex flex-col">
                <span>{m.label}</span>
                {m.hint && <span className="text-[11px] text-muted-foreground/70">{m.hint}</span>}
              </div>
            </TableCell>
            {summaries.map((s) => (
              <TableCell key={s.model} className="text-right font-medium tabular-nums">
                {(s[m.key] as number).toFixed(3)}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
