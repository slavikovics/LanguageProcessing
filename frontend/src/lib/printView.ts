export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function inlineMarkdownToHtml(text: string): string {
  return escapeHtml(text)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>')
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");
}

export function markdownToPrintHtml(markdown: string): string {
  const parts: string[] = [];
  let listBuffer: string[] = [];
  let paragraphBuffer: string[] = [];

  const flushList = () => {
    if (listBuffer.length > 0) {
      parts.push(`<ul>${listBuffer.map((item) => `<li>${inlineMarkdownToHtml(item)}</li>`).join("")}</ul>`);
      listBuffer = [];
    }
  };
  const flushParagraph = () => {
    if (paragraphBuffer.length > 0) {
      parts.push(`<p>${inlineMarkdownToHtml(paragraphBuffer.join(" "))}</p>`);
      paragraphBuffer = [];
    }
  };

  for (const rawLine of markdown.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (line === "") {
      flushParagraph();
      flushList();
      continue;
    }
    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      flushParagraph();
      flushList();
      const level = Math.min(heading[1].length + 2, 6);
      parts.push(`<h${level}>${inlineMarkdownToHtml(heading[2])}</h${level}>`);
      continue;
    }
    const listItem = /^[-*]\s+(.*)$/.exec(line);
    if (listItem) {
      flushParagraph();
      listBuffer.push(listItem[1]);
      continue;
    }
    flushList();
    paragraphBuffer.push(line);
  }
  flushParagraph();
  flushList();
  return parts.join("");
}

export function openPrintView(title: string, bodyHtml: string): void {
  const html = `<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8" />
<title>${escapeHtml(title)}</title>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body {
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    max-width: 860px;
    margin: 2rem auto;
    padding: 0 1.5rem 2rem;
    color: #111827;
    line-height: 1.55;
  }
  h1 { font-size: 1.4rem; margin: 0 0 0.25rem; }
  h2 { font-size: 1.05rem; margin: 1.75rem 0 0.5rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.25rem; }
  h3, h4, h5, h6 { margin: 1em 0 0.4em; }
  .meta { color: #6b7280; font-size: 0.85rem; margin: 0 0 1.25rem; }
  .subtle { color: #6b7280; font-size: 0.85rem; margin: -0.25rem 0 0.5rem; }
  p { margin: 0.5rem 0; }
  ul { margin: 0.4em 0; padding-left: 1.4rem; }
  li { margin: 0.15em 0; }
  ul.keyword-tree { padding-left: 1.1rem; margin: 0.25rem 0; }
  ul.keyword-tree ul { padding-left: 1.25rem; margin: 0.15rem 0; }
  ul.keyword-tree li { margin: 0.15rem 0; }
  table { border-collapse: collapse; width: 100%; margin-top: 0.5rem; }
  th, td { border: 1px solid #d1d5db; padding: 6px 10px; text-align: left; font-size: 0.9rem; }
  th { background: #f3f4f6; }
  @media print {
    body { margin: 0; padding: 1rem; }
    a { color: inherit; text-decoration: none; }
  }
</style>
</head>
<body>${bodyHtml}</body>
</html>`;

  const url = URL.createObjectURL(new Blob([html], { type: "text/html" }));
  const printWindow = window.open(url, "_blank");
  if (!printWindow) {
    URL.revokeObjectURL(url);
    return;
  }
  printWindow.addEventListener("load", () => {
    printWindow.print();
  });
  printWindow.addEventListener("unload", () => {
    URL.revokeObjectURL(url);
  });
}
