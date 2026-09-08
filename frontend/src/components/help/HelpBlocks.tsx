import type { ReactNode } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function Feature({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 rounded-md border p-3 transition-colors duration-150 hover:bg-accent/40">
      <span className="text-sm font-medium">{title}</span>
      <p className="text-sm text-muted-foreground">{children}</p>
    </div>
  );
}

export function MetricEntry(
  {
    id,
    title,
    formula,
    children,
  }: {
    id: string;
    title: string;
    formula?: string;
    children: ReactNode;
  }
) {
  return (
    <div
      id={id}
      className="scroll-mt-24 rounded-md border p-3 transition-colors duration-150 target:border-primary target:bg-primary/5"
    >
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span className="text-sm font-medium">{title}</span>
        {formula && (
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground">{formula}</code>
        )}
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{children}</p>
    </div>
  );
}

export function ProcessSteps({ steps }: { steps: { title: string; children: ReactNode }[] }) {
  return (
    <ol className="flex flex-col">
      {steps.map((step, i) => (
        <li key={i} className="relative flex gap-4 pb-6 last:pb-0">
          {i < steps.length - 1 && (
            <span
              aria-hidden
              className="absolute top-7 left-[13px] h-[calc(100%-1.25rem)] w-px bg-border"
            />
          )}
          <span className="relative z-10 flex size-7 shrink-0 items-center justify-center rounded-full border bg-background text-xs font-semibold">
            {i + 1}
          </span>
          <div className="flex flex-col gap-1 pt-0.5">
            <span className="text-sm font-medium">{step.title}</span>
            <p className="text-sm text-muted-foreground">{step.children}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function RomipLink() {
  return (
    <a
      href="/romip_metrics.pdf"
      target="_blank"
      rel="noreferrer"
      className="text-primary underline-offset-2 hover:underline"
    >
      ROMIP&apos;2004
    </a>
  );
}

export function Section({
  icon: Icon,
  title,
  description,
  id,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: ReactNode;
  id?: string;
  children: ReactNode;
}) {
  return (
    <Card id={id} className="scroll-mt-24 transition-shadow duration-200 hover:shadow-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Icon className="size-4" />
          </span>
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">{children}</CardContent>
    </Card>
  );
}
