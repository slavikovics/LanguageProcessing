import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import remarkGfm from "remark-gfm";

import { makeMarkdownComponents } from "./components/markdownComponents";
import { useMarkdownTheme } from "./useMarkdownTheme";

export function MarkdownContent({
  content,
  className,
  compact = false,
  theme,
}: {
  content: string;
  className?: string;
  compact?: boolean;
  theme?: "light" | "dark";
}) {
  const resolvedTheme = useMarkdownTheme(theme);
  const components = makeMarkdownComponents({ compact, theme: resolvedTheme });

  return (
    <div className={className}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
