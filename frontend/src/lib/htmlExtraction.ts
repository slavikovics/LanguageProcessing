/** Strips <script>/<style>, pulls <title> and body text out of an uploaded
 * HTML file — client-side, so picking a file gives immediate feedback
 * without a server round trip. Shared by CollectionsPage's document form and
 * the LR2 language-ID module's ad-hoc HTML upload. */
export function extractFromHtml(html: string): { title: string; text: string } {
  const doc = new DOMParser().parseFromString(html, "text/html");
  doc.querySelectorAll("script, style, noscript").forEach((el) => el.remove());
  const title = doc.querySelector("title")?.textContent?.trim() ?? "";
  const text = (doc.body?.textContent ?? "").replace(/\s+/g, " ").trim();
  return { title, text };
}
