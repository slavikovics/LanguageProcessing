import type { PrecisionRecallCurve } from "@/api/types";

interface PrecisionRecallChartProps {
  curve: PrecisionRecallCurve;
  width?: number;
  height?: number;
}

const LEVELS = [0, 0.25, 0.5, 0.75, 1];

export function PrecisionRecallChart({
  curve,
  width = 380,
  height = 220,
}: PrecisionRecallChartProps) {
  const padding = 34;
  const innerW = width - padding * 2;
  const innerH = height - padding * 2;

  const toX = (recall: number) => padding + recall * innerW;
  const toY = (precision: number) => padding + (1 - precision) * innerH;

  const points = curve.map(([recall, precision]) => `${toX(recall)},${toY(precision)}`).join(" ");

  return (
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
          <text
            x={padding - 6}
            y={toY(t) + 3}
            textAnchor="end"
            className="fill-muted-foreground text-[9px]"
          >
            {t.toFixed(2)}
          </text>
          <text
            x={toX(t)}
            y={height - padding + 14}
            textAnchor="middle"
            className="fill-muted-foreground text-[9px]"
          >
            {t.toFixed(2)}
          </text>
        </g>
      ))}
      {curve.length > 0 && (
        <>
          <polyline
            points={points}
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            className="text-primary"
          />
          {curve.map(([recall, precision], i) => (
            <circle key={i} cx={toX(recall)} cy={toY(precision)} r={2.5} className="fill-primary" />
          ))}
        </>
      )}
      <text x={width / 2} y={height - 4} textAnchor="middle" className="fill-muted-foreground text-[10px]">
        Recall
      </text>
      <text
        x={10}
        y={height / 2}
        textAnchor="middle"
        className="fill-muted-foreground text-[10px]"
        transform={`rotate(-90 10 ${height / 2})`}
      >
        Precision
      </text>
    </svg>
  );
}
