import { LANG_ID_METHOD_LABELS, type LangIdRunSummary } from "../api/types";

import { useMeasuredWidth } from "@/hooks/useMeasuredWidth";
import { colorForModel } from "@/lib/modelColors";

/** One bar per method — simpler than the Metrics page's QueryMetricBarChart
 * (no per-query grouping needed here), reused for both the accuracy and
 * the speed comparison via `valueOf`/`formatValue`. */
export function LangIdSummaryBarChart({
  summaries,
  valueOf,
  formatValue,
  ariaLabel,
  height = 220,
}: {
  summaries: LangIdRunSummary[];
  valueOf: (summary: LangIdRunSummary) => number;
  formatValue: (value: number) => string;
  ariaLabel: string;
  height?: number;
}) {
  const { ref, width } = useMeasuredWidth<HTMLDivElement>();
  const padding = { top: 24, right: 16, bottom: 28, left: 8 };
  const innerW = Math.max(0, width - padding.left - padding.right);
  const innerH = height - padding.top - padding.bottom;

  const values = summaries.map(valueOf);
  const maxValue = Math.max(...values, 0.0001);

  const slotW = summaries.length > 0 ? innerW / summaries.length : 0;
  const barW = Math.max(16, Math.min(96, slotW * 0.6));

  return (
    <div ref={ref} className="w-full" style={{ minHeight: height }}>
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label={ariaLabel}>
          <line
            x1={padding.left}
            x2={width - padding.right}
            y1={padding.top + innerH}
            y2={padding.top + innerH}
            stroke="currentColor"
            className="text-border"
          />
          {summaries.map((summary, i) => {
            const value = valueOf(summary);
            const barH = maxValue > 0 ? (value / maxValue) * innerH : 0;
            const x = padding.left + i * slotW + (slotW - barW) / 2;
            const y = padding.top + innerH - barH;
            return (
              <g key={summary.method}>
                <title>{`${LANG_ID_METHOD_LABELS[summary.method]}: ${formatValue(value)}`}</title>
                <rect x={x} y={y} width={barW} height={barH} rx={3} fill={colorForModel(summary.method)} />
                <text x={x + barW / 2} y={y - 6} textAnchor="middle" className="fill-foreground text-[11px] font-medium tabular-nums">
                  {formatValue(value)}
                </text>
                <text
                  x={x + barW / 2}
                  y={padding.top + innerH + 14}
                  textAnchor="middle"
                  className="fill-muted-foreground text-[10px]"
                >
                  {LANG_ID_METHOD_LABELS[summary.method]}
                </text>
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}
