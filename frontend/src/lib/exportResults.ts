/** Client-side "save to file" for LR2's language-ID results — no server
 * endpoint or library needed, just a Blob and a throwaway <a download>. */
function downloadBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function downloadJson(filename: string, data: unknown): void {
  downloadBlob(filename, new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
}

function csvCell(value: unknown): string {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function downloadCsv(filename: string, rows: Record<string, unknown>[]): void {
  if (rows.length === 0) {
    downloadBlob(filename, new Blob([""], { type: "text/csv" }));
    return;
  }
  const headers = Object.keys(rows[0]);
  const lines = [
    headers.map(csvCell).join(","),
    ...rows.map((row) => headers.map((key) => csvCell(row[key])).join(",")),
  ];
  downloadBlob(filename, new Blob([lines.join("\n")], { type: "text/csv" }));
}
