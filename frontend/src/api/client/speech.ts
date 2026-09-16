import type { SpeechCommand } from "../types";
import { API_BASE_URL, request, webSocketUrl } from "./http";

export function speechStreamWebSocketUrl(): string {
  return webSocketUrl("/speech/stt/stream");
}

export async function synthesizeSpeech(
  input: { text: string; voice?: string | null; rate?: number },
  { signal }: { signal?: AbortSignal } = {},
): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/speech/tts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: input.text,
      voice: input.voice ?? null,
      rate: input.rate ?? 1.0,
    }),
    signal,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }
  const buffer = await response.arrayBuffer();
  return new Blob([fixWavHeaderSize(buffer)], { type: "audio/wav" });
}

// Backend writes a placeholder 0xFFFFFFFF size; browsers can hang decoding that.
function fixWavHeaderSize(buffer: ArrayBuffer): ArrayBuffer {
  const view = new DataView(buffer);
  const totalSize = buffer.byteLength;
  view.setUint32(4, totalSize - 8, true);
  view.setUint32(40, totalSize - 44, true);
  return buffer;
}

export function listSpeechCommands(): Promise<SpeechCommand[]> {
  return request<SpeechCommand[]>("/speech/commands");
}

export function createSpeechCommand(input: {
  phrase: string;
  action: string;
  language?: string;
  is_active?: boolean;
}): Promise<SpeechCommand> {
  return request<SpeechCommand>("/speech/commands", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateSpeechCommand(
  id: number,
  input: Partial<{ phrase: string; action: string; language: string; is_active: boolean }>,
): Promise<SpeechCommand> {
  return request<SpeechCommand>(`/speech/commands/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteSpeechCommand(id: number): Promise<void> {
  return request<void>(`/speech/commands/${id}`, { method: "DELETE" });
}
