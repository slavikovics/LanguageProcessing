import { FileUp } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { createDocument, getDocument, updateDocument } from "../api/client";
import type { DocumentSummary } from "../api/types";
import { extractFromHtml } from "../lib/htmlExtraction";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function DocumentFormDialog({
  mode,
  collectionId,
  editingDocument,
  onClose,
  onSaved,
}: {
  mode: "closed" | "create" | "edit";
  collectionId: number | null;
  editingDocument: DocumentSummary | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const titleInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (mode === "create") {
      setTitle("");
      setUrl("");
      setText("");
      setError(null);
    } else if (mode === "edit" && editingDocument !== null) {
      setError(null);
      setTitle(editingDocument.title);
      setUrl(editingDocument.url ?? "");
      setText("Загрузка…");
      void (async () => {
        try {
          const detail = await getDocument(editingDocument.id);
          setText(detail.clean_text);
        } catch (err) {
          setError(err instanceof Error ? err.message : String(err));
          setText("");
        }
      })();
    }
  }, [mode, editingDocument]);

  async function handleHtmlFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const html = await file.text();
    const extracted = extractFromHtml(html);
    if (extracted.title) setTitle(extracted.title);
    setText(extracted.text);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (collectionId === null) return;
    setSubmitting(true);
    setError(null);
    try {
      const input = { title, url: url.trim() || null, clean_text: text };
      if (mode === "create") {
        await createDocument(collectionId, input);
      } else if (mode === "edit" && editingDocument !== null) {
        await updateDocument(editingDocument.id, input);
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={mode !== "closed"} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent
        className="max-w-2xl"
        onOpenAutoFocus={(event) => {
          // Radix focuses the first tabbable field (the title input) on
          // open, which selects its whole value — collapse the caret to
          // the end instead of leaving the title highlighted.
          event.preventDefault();
          const el = titleInputRef.current;
          if (el) {
            el.focus({ preventScroll: true });
            const end = el.value.length;
            el.setSelectionRange(end, end);
          }
        }}
      >
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "Новый документ" : "Редактирование документа"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div className="grid gap-1.5">
            <Label>Заголовок</Label>
            <Input ref={titleInputRef} value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          <div className="grid gap-1.5">
            <Label>
              URL <span className="text-muted-foreground">(необязательно)</span>
            </Label>
            <Input type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.com/" />
          </div>
          <div className="grid gap-1.5">
            <div className="flex items-center justify-between">
              <Label>Текст документа</Label>
              <Button type="button" variant="ghost" size="sm" onClick={() => fileInputRef.current?.click()}>
                <FileUp className="size-3.5" />
                Загрузить HTML-файл
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".html,.htm,text/html"
                className="hidden"
                onChange={handleHtmlFile}
              />
            </div>
            <Textarea value={text} onChange={(e) => setText(e.target.value)} className="h-40" required />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose}>
              Отмена
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Сохранение…" : mode === "create" ? "Создать" : "Сохранить"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
