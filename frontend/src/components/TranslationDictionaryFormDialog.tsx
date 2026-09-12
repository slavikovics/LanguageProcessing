import { useEffect, useState, type FormEvent } from "react";

import {
  createTranslationDictionaryEntry,
  updateTranslationDictionaryEntry,
} from "@/api/client";
import type { TranslationDictionaryEntry } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

const ANY_POS = "ANY";

const POS_TAGS = [
  "ADJ",
  "ADP",
  "ADV",
  "AUX",
  "CCONJ",
  "DET",
  "INTJ",
  "NOUN",
  "NUM",
  "PART",
  "PRON",
  "PROPN",
  "PUNCT",
  "SCONJ",
  "SYM",
  "VERB",
  "X",
];

export function TranslationDictionaryFormDialog({
  mode,
  editingEntry,
  onClose,
  onSaved,
}: {
  mode: "closed" | "create" | "edit";
  editingEntry: TranslationDictionaryEntry | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [sourceLemma, setSourceLemma] = useState("");
  const [pos, setPos] = useState(ANY_POS);
  const [targetText, setTargetText] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mode === "create") {
      setSourceLemma("");
      setPos(ANY_POS);
      setTargetText("");
      setNotes("");
      setError(null);
    } else if (mode === "edit" && editingEntry !== null) {
      setSourceLemma(editingEntry.source_lemma);
      setPos(editingEntry.pos && editingEntry.pos !== "*" ? editingEntry.pos : ANY_POS);
      setTargetText(editingEntry.target_text);
      setNotes(editingEntry.notes ?? "");
      setError(null);
    }
  }, [mode, editingEntry]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "create") {
        await createTranslationDictionaryEntry({
          source_lemma: sourceLemma,
          pos: pos === ANY_POS ? null : pos,
          target_text: targetText,
          notes: notes.trim() || null,
        });
      } else if (mode === "edit" && editingEntry !== null) {
        await updateTranslationDictionaryEntry(editingEntry.id, {
          target_text: targetText,
          pos: pos === ANY_POS ? null : pos,
          notes: notes.trim() || null,
        });
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
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "Новая словарная статья" : "Редактирование статьи"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div className="grid gap-1.5">
            <Label>Слово (лемма, английский)</Label>
            <Input
              value={sourceLemma}
              onChange={(event) => setSourceLemma(event.target.value)}
              disabled={mode === "edit"}
              required
            />
          </div>
          <div className="grid gap-1.5">
            <Label>Часть речи</Label>
            <Select value={pos} onValueChange={setPos}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY_POS}>Любая</SelectItem>
                {POS_TAGS.map((tag) => (
                  <SelectItem key={tag} value={tag}>
                    {tag}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-1.5">
            <Label>Перевод (французский)</Label>
            <Input value={targetText} onChange={(event) => setTargetText(event.target.value)} required />
          </div>
          <div className="grid gap-1.5">
            <Label>
              Примечания <span className="text-muted-foreground">(необязательно)</span>
            </Label>
            <Textarea value={notes} onChange={(event) => setNotes(event.target.value)} className="h-20" />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={onClose}>
              Отмена
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Сохранение…" : mode === "create" ? "Добавить" : "Сохранить"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
