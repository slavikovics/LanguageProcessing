import type { Components } from "react-markdown";

import { cn } from "@/lib/utils";
import { CodeBlock } from "./CodeBlock";

export function makeMarkdownComponents({
  compact,
  theme,
}: {
  compact: boolean;
  theme: "light" | "dark";
}): Components {
  const headingSpacing = compact ? "mt-3 mb-1.5" : "mt-5 mb-2";
  const paragraphSpacing = compact ? "my-1.5" : "my-2.5";

  return {
    h1: ({ children }) => (
      <h1 className={cn("text-xl font-semibold", headingSpacing)}>{children}</h1>
    ),
    h2: ({ children }) => (
      <h2 className={cn("text-lg font-semibold", headingSpacing)}>{children}</h2>
    ),
    h3: ({ children }) => (
      <h3 className={cn("text-base font-semibold", headingSpacing)}>{children}</h3>
    ),
    h4: ({ children }) => (
      <h4 className={cn("text-sm font-semibold", headingSpacing)}>{children}</h4>
    ),
    h5: ({ children }) => (
      <h5 className={cn("text-sm font-semibold", headingSpacing)}>{children}</h5>
    ),
    h6: ({ children }) => (
      <h6 className={cn("text-sm font-semibold text-muted-foreground", headingSpacing)}>
        {children}
      </h6>
    ),
    p: ({ children }) => <p className={cn("text-sm leading-relaxed", paragraphSpacing)}>{children}</p>,
    strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
    em: ({ children }) => <em className="italic">{children}</em>,
    del: ({ children }) => <del className="text-muted-foreground line-through">{children}</del>,
    ul: ({ children }) => <ul className={cn("list-disc pl-5 text-sm", paragraphSpacing)}>{children}</ul>,
    ol: ({ children }) => <ol className={cn("list-decimal pl-5 text-sm", paragraphSpacing)}>{children}</ol>,
    li: ({ children, className }) => (
      <li
        className={cn(
          "my-0.5 marker:text-muted-foreground",
          className?.includes("task-list-item") && "list-none -ml-5",
        )}
      >
        {children}
      </li>
    ),
    input: ({ type, checked }) =>
      type === "checkbox" ? (
        <input
          type="checkbox"
          checked={!!checked}
          disabled
          readOnly
          className="mr-1.5 align-middle accent-primary"
        />
      ) : null,
    blockquote: ({ children }) => (
      <blockquote className="my-2 border-l-2 border-border pl-3 text-sm text-muted-foreground italic">
        {children}
      </blockquote>
    ),
    hr: () => <hr className="my-4 border-border" />,
    a: ({ href, children }) => (
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className="text-primary underline-offset-2 hover:underline"
      >
        {children}
      </a>
    ),
    img: ({ src, alt }) => (
      <img src={src} alt={alt} className="my-2 max-w-full rounded-md border" />
    ),
    table: ({ children }) => (
      <div className="my-3 overflow-x-auto rounded-md border">
        <table className="w-full border-collapse text-sm">{children}</table>
      </div>
    ),
    thead: ({ children }) => <thead className="bg-muted">{children}</thead>,
    tbody: ({ children }) => <tbody>{children}</tbody>,
    tr: ({ children }) => <tr className="border-b last:border-b-0">{children}</tr>,
    th: ({ children }) => <th className="px-3 py-1.5 text-left font-medium">{children}</th>,
    td: ({ children }) => <td className="px-3 py-1.5 align-top">{children}</td>,
    code: ({ className, children }) => {
      const match = /language-(\w+)/.exec(className ?? "");
      const text = String(children ?? "");
      const isInline = !match && !text.includes("\n");
      if (isInline) {
        return (
          <code className="rounded bg-muted px-1 py-0.5 font-mono text-[0.85em]">{children}</code>
        );
      }
      return (
        <CodeBlock language={match?.[1] ?? null} theme={theme}>
          {text.replace(/\n$/, "")}
        </CodeBlock>
      );
    },
  };
}
