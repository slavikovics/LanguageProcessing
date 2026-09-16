import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import oneDark from "react-syntax-highlighter/dist/esm/styles/prism/one-dark";
import oneLight from "react-syntax-highlighter/dist/esm/styles/prism/one-light";

import { cn } from "@/lib/utils";
import { resolveLanguage } from "../languageMap";

export function CodeBlock({
  language,
  theme,
  children,
}: {
  language: string | null;
  theme: "light" | "dark";
  children: string;
}) {
  const [copied, setCopied] = useState(false);
  const { prism, label } = resolveLanguage(language);
  const code = children.replace(/\n$/, "");

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard access can be blocked by browser permissions; fail silently.
    }
  }

  return (
    <div className="my-3 overflow-hidden rounded-md border">
      <div className="flex items-center justify-between border-b bg-muted px-3 py-1.5">
        <span className="text-xs text-muted-foreground">{label}</span>
        <button
          type="button"
          onClick={handleCopy}
          className={cn(
            "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
          )}
        >
          {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
          {copied ? "Скопировано" : "Копировать"}
        </button>
      </div>
      <SyntaxHighlighter
        language={prism}
        style={theme === "dark" ? oneDark : oneLight}
        customStyle={{ margin: 0, padding: "0.75rem", fontSize: "0.8rem", background: "transparent" }}
        wrapLongLines
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
