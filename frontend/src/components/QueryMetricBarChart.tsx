import { ModelSwatch } from "@/components/ModelSwatch";
import { useMeasuredWidth } from "@/hooks/useMeasuredWidth";
import type { QueryMetrics } from "../api/types";

export interface QuerySeries {
  key: string;
  label: string;
  color: string;
  queries: QueryMetrics[];
}

const BAR_CHART_LEVELS = [0, 0.25, 0.5, 0.75, 1];
const BAR_LABEL_MAX_LINES = 3;
const BAR_LABEL_CHARS_PER_LINE = 12;

function wrapLabel(text: string, maxCharsPerLine = BAR_LABEL_CHARS_PER_LINE, maxLines = BAR_LABEL_MAX_LINES): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length > maxCharsPerLine && current) {
      lines.push(current);
      current = word;
    } else {
      current = candidate;
    }
  }
  if (current) lines.push(current);
  if (lines.length > maxLines) {
    const shown = lines.slice(0, maxLines);
    shown[maxLines - 1] = `${shown[maxLines - 1].slice(0, maxCharsPerLine - 1)}…`;
    return shown;
  }
  return lines;
}

export function QueryMetricBarChart({
  series,
  metricKey,
  onSelectQuery,
  height = 380,
}: {
  series: QuerySeries[];
  metricKey: keyof QueryMetrics
  onSelectQuery: (text: string) => void
  height?: number;
}) {
  const { ref, width } = useMeasuredWidth<HTMLDivElement>();
  const padding = { top: 24, right: 16, bottom: 16 + BAR_LABEL_MAX_LINES * 13, left: 34 };
  const innerW = Math.max(0, width - padding.left - padding.right);
  const innerH = height - padding.top - padding.bottom;

  const queryTexts: string[] = [];
  const seen = new Set<string>();
  for (const s of series) {
    for (const q of s.queries) {
      if (!seen.has(q.query_text)) {
        seen.add(q.query_text);
        queryTexts.push(q.query_text);
      }
    }
  }

  const n = queryTexts.length;
  const slotW = n > 0 ? innerW / n : 0;
  const groupW = Math.max(10, Math.min(120, slotW * 0.7));
  const barW = series.length > 0 ? groupW / series.length : groupW;
  const singleSeries = series.length === 1;

  const toY = (value: number) => padding.top + (1 - value) * innerH;

  return (
    <div ref={ref} className="w-full" style={{ minHeight: height }}>
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label="Метрика по запросам">
          {BAR_CHART_LEVELS.map((level) => (
            <g key={level}>
              <line
                x1={padding.left}
                x2={width - padding.right}
                y1={toY(level)}
                y2={toY(level)}
                stroke="currentColor"
                className="text-border/40"
              />
              <text x={padding.left - 8} y={toY(level) + 3} textAnchor="end" className="fill-muted-foreground text-[10px]">
                {level.toFixed(2)}
              </text>
            </g>
          ))}
          <line
            x1={padding.left}
            x2={padding.left}
            y1={padding.top}
            y2={padding.top + innerH}
            stroke="currentColor"
            className="text-border"
          />
          <line
            x1={padding.left}
            x2={width - padding.right}
            y1={padding.top + innerH}
            y2={padding.top + innerH}
            stroke="currentColor"
            className="text-border"
          />
          {queryTexts.map((text, qi) => {
            const groupX = padding.left + qi * slotW + (slotW - groupW) / 2;
            const lines = wrapLabel(text);
            return (
              <g key={text}>
                {series.map((s, si) => {
                  const q = s.queries.find((qq) => qq.query_text === text);
                  if (!q) return null;
                  const value = q[metricKey] as number;
                  const x = groupX + si * barW;
                  const y = toY(value);
                  const barH = Math.max(0, padding.top + innerH - y);
                  return (
                    <g key={s.key}>
                      <title>{`${s.label} — ${text}: ${value.toFixed(2)}`}</title>
                      <rect x={x} y={y} width={Math.max(2, barW - 2)} height={barH} rx={2} fill={s.color} />
                      {singleSeries && (
                        <text
                          x={x + barW / 2}
                          y={y - 6}
                          textAnchor="middle"
                          className="fill-foreground text-[11px] font-medium tabular-nums"
                        >
                          {value.toFixed(2)}
                        </text>
                      )}
                    </g>
                  );
                })}
                <g
                  role="button"
                  tabIndex={0}
                  onClick={() => onSelectQuery(text)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelectQuery(text);
                    }
                  }}
                  aria-label={`Показать полный текст запроса: ${text}`}
                  className="cursor-pointer outline-none"
                >
                  {}
                  <rect
                    x={groupX - 4}
                    y={padding.top + innerH}
                    width={groupW + 8}
                    height={BAR_LABEL_MAX_LINES * 13 + 16}
                    fill="transparent"
                  />
                  {lines.map((line, li) => (
                    <text
                      key={li}
                      x={groupX + groupW / 2}
                      y={padding.top + innerH + 16 + li * 13}
                      textAnchor="middle"
                      className="fill-muted-foreground text-[10px] transition-colors hover:fill-foreground hover:underline"
                    >
                      {line}
                    </text>
                  ))}
                </g>
              </g>
            );
          })}
        </svg>
      )}
      {series.length > 1 && (
        <div className="flex flex-wrap gap-3 pt-2">
          {series.map((s) => (
            <ModelSwatch key={s.key} label={s.label} color={s.color} />
          ))}
        </div>
      )}
    </div>
  );
}
