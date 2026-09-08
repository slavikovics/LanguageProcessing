import { useMeasuredWidth } from "@/hooks/useMeasuredWidth";

export interface LossPoint {
  epoch: number;
  loss: number;
}

export function LossCurveChart({ points, height = 160 }: { points: LossPoint[]; height?: number }) {
  const { ref, width } = useMeasuredWidth<HTMLDivElement>();
  const padding = { top: 12, right: 12, bottom: 20, left: 34 };
  const innerW = Math.max(0, width - padding.left - padding.right);
  const innerH = height - padding.top - padding.bottom;

  const maxLoss = Math.max(...points.map((p) => p.loss), 0.001);
  const maxEpoch = Math.max(...points.map((p) => p.epoch), 1);

  const toX = (epoch: number) => padding.left + (epoch / maxEpoch) * innerW;
  const toY = (loss: number) => padding.top + (1 - loss / maxLoss) * innerH;

  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${toX(p.epoch)},${toY(p.loss)}`).join(" ");

  return (
    <div ref={ref} className="w-full" style={{ minHeight: height }}>
      {width > 0 && points.length > 0 && (
        <svg width={width} height={height} role="img" aria-label="Кривая обучения (loss)">
          <line
            x1={padding.left}
            x2={width - padding.right}
            y1={padding.top + innerH}
            y2={padding.top + innerH}
            stroke="currentColor"
            className="text-border"
          />
          <line
            x1={padding.left}
            x2={padding.left}
            y1={padding.top}
            y2={padding.top + innerH}
            stroke="currentColor"
            className="text-border"
          />
          <text x={padding.left - 6} y={padding.top + 4} textAnchor="end" className="fill-muted-foreground text-[10px]">
            {maxLoss.toFixed(2)}
          </text>
          <text x={padding.left - 6} y={padding.top + innerH} textAnchor="end" className="fill-muted-foreground text-[10px]">
            0
          </text>
          <path d={path} fill="none" stroke="#2563eb" strokeWidth={1.5} />
          <text
            x={width - padding.right}
            y={padding.top + innerH + 14}
            textAnchor="end"
            className="fill-muted-foreground text-[10px]"
          >
            эпоха {maxEpoch}
          </text>
        </svg>
      )}
    </div>
  );
}
