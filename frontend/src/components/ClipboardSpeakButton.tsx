import { ClipboardPaste } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useSpeechPlayback } from "@/context/SpeechPlaybackContext";

export function ClipboardSpeakButton({ onText }: { onText?: (text: string) => void }) {
  const { speak } = useSpeechPlayback();
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setError(null);
    let text: string;
    try {
      text = (await navigator.clipboard.readText()).trim();
    } catch {
      setError("Нет доступа к буферу обмена — разрешите его в браузере.");
      return;
    }
    if (!text) {
      setError("Буфер обмена пуст.");
      return;
    }
    onText?.(text);
    speak(text);
  }

  return (
    <div className="inline-flex items-center gap-2">
      <Button type="button" variant="outline" size="sm" onClick={handleClick}>
        <ClipboardPaste className="size-4" />
        Озвучить из буфера
      </Button>
      {error && <span className="text-xs text-destructive">{error}</span>}
    </div>
  );
}
