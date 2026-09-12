export interface LanguageInfo {
  prism: string;
  label: string;
}

const LANGUAGE_MAP: Record<string, LanguageInfo> = {
  js: { prism: "javascript", label: "JavaScript" },
  javascript: { prism: "javascript", label: "JavaScript" },
  jsx: { prism: "jsx", label: "JSX" },
  ts: { prism: "typescript", label: "TypeScript" },
  typescript: { prism: "typescript", label: "TypeScript" },
  tsx: { prism: "tsx", label: "TSX" },
  py: { prism: "python", label: "Python" },
  python: { prism: "python", label: "Python" },
  json: { prism: "json", label: "JSON" },
  bash: { prism: "bash", label: "Bash" },
  sh: { prism: "bash", label: "Shell" },
  shell: { prism: "bash", label: "Shell" },
  sql: { prism: "sql", label: "SQL" },
  html: { prism: "markup", label: "HTML" },
  xml: { prism: "markup", label: "XML" },
  css: { prism: "css", label: "CSS" },
  java: { prism: "java", label: "Java" },
  c: { prism: "c", label: "C" },
  cpp: { prism: "cpp", label: "C++" },
  "c++": { prism: "cpp", label: "C++" },
  go: { prism: "go", label: "Go" },
  rust: { prism: "rust", label: "Rust" },
  rs: { prism: "rust", label: "Rust" },
  yaml: { prism: "yaml", label: "YAML" },
  yml: { prism: "yaml", label: "YAML" },
  markdown: { prism: "markdown", label: "Markdown" },
  md: { prism: "markdown", label: "Markdown" },
  diff: { prism: "diff", label: "Diff" },
  dockerfile: { prism: "docker", label: "Dockerfile" },
};

export function resolveLanguage(fence: string | null | undefined): LanguageInfo {
  if (!fence) return { prism: "text", label: "Текст" };
  const key = fence.toLowerCase();
  return LANGUAGE_MAP[key] ?? { prism: key, label: fence };
}
