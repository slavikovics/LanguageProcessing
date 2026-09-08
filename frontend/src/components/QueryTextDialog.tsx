import { Check, Copy } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export function QueryTextDialog({ query, onClose }: { query: string | null; onClose: () => void }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setCopied(false);
  }, [query]);

  async function handleCopy() {
    if (!query) return;
    try {
      await navigator.clipboard.writeText(query);
      setCopied(true);
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <Dialog open={query !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Текст запроса</DialogTitle>
        </DialogHeader>
        <p className="rounded-md border bg-muted/30 p-3 text-sm break-words whitespace-pre-wrap">{query}</p>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleCopy}>
            {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
            {copied ? "Скопировано" : "Скопировать"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
