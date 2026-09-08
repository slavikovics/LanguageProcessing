export function extractFromHtml(html: string): { title: string; text: string } {
  const doc = new DOMParser().parseFromString(html, "text/html");
  doc.querySelectorAll("script, style, noscript").forEach((el) => el.remove());
  const title = doc.querySelector("title")?.textContent?.trim() ?? "";
  const text = (doc.body?.textContent ?? "").replace(/\s+/g, " ").trim();
  return { title, text };
}
