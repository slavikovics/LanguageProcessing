import { Progress } from "@/components/ui/progress";

interface ProgressBarProps {
  value: number;
  max: number
  complete?: boolean
}

export function ProgressBar({ value, max, complete = false }: ProgressBarProps) {
  const pct = complete ? 100 : max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className="flex items-center gap-3">
      <Progress value={pct} max={max} className="flex-1" />
      <span className="whitespace-nowrap text-xs text-muted-foreground">
        {value} / {max} ({pct}%)
      </span>
    </div>
  );
}
