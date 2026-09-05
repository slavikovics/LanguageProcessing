import { useMeasuredWidth } from "@/hooks/useMeasuredWidth";
import type { PrecisionRecallCurve } from "@/api/types";

export interface CurveSeries {
  key: string;
  label: string;
  color: string;
  points: PrecisionRecallCurve;
}

interface PrecisionRecallChartProps {
  curves: CurveSeries[];
  height?: number;
}

const LEVELS = [0, 0.25, 0.5, 0.75, 1];

export function PrecisionRecallChart({ curves, height = 320 }: PrecisionRecallChartProps) {
  const { ref, width } = useMeasuredWidth<HTMLDivElement>();
  const padding = 40;
  const innerW = Math.max(0, width - padding * 2);
  const innerH = height - padding * 2;

  const toX = (recall: number) => padding + recall * innerW;
  const toY = (precision: number) => padding + (1 - precision) * innerH;

  return (
    <div className="flex flex-col gap-3">
      <div ref={ref} className="w-full">
        {width > 0 && (
          <svg
            width={width}
            height={height}
            viewBox={`0 0 ${width} ${height}`}
            role="img"
            aria-label="11-точечная кривая Precision/Recall"
          >
            <line
              x1={padding}
              y1={padding}
              x2={padding}
              y2={height - padding}
              stroke="currentColor"
              className="text-border"
            />
            <line
              x1={padding}
              y1={height - padding}
              x2={width - padding}
              y2={height - padding}
              stroke="currentColor"
              className="text-border"
            />
            {LEVELS.map((t) => (
              <g key={t}>
                <line
                  x1={padding}
                  y1={toY(t)}
                  x2={width - padding}
                  y2={toY(t)}
                  stroke="currentColor"
                  className="text-border/40"
                />
                <text
                  x={padding - 8}
                  y={toY(t) + 3}
                  textAnchor="end"
                  className="fill-muted-foreground text-[10px]"
                >
                  {t.toFixed(2)}
                </text>
                <text
                  x={toX(t)}
                  y={height - padding + 16}
                  textAnchor="middle"
                  className="fill-muted-foreground text-[10px]"
                >
                  {t.toFixed(2)}
                </text>
              </g>
            ))}
            {curves.map((series) => {
              if (series.points.length === 0) return null;
              const points = series.points
                .map(([recall, precision]) => `${toX(recall)},${toY(precision)}`)
                .join(" ");
              return (
                <g key={series.key}>
                  <polyline points={points} fill="none" stroke={series.color} strokeWidth={2} />
                  {series.points.map(([recall, precision], i) => (
                    <circle key={i} cx={toX(recall)} cy={toY(precision)} r={3} fill={series.color} />
                  ))}
                </g>
              );
            })}
            <text x={width / 2} y={height - 6} textAnchor="middle" className="fill-muted-foreground text-[11px]">
              Recall
            </text>
            <text
              x={12}
              y={height / 2}
              textAnchor="middle"
              className="fill-muted-foreground text-[11px]"
              transform={`rotate(-90 12 ${height / 2})`}
            >
              Precision
            </text>
          </svg>
        )}
      </div>
      {curves.length > 1 && (
        <div className="flex flex-wrap gap-3">
          {curves.map((series) => (
            <div key={series.key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="inline-block size-2.5 rounded-full" style={{ backgroundColor: series.color }} />
              {series.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
