import { HelpCircle, Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
  createSpeechCommand,
  deleteSpeechCommand,
  listSpeechCommands,
  updateSpeechCommand,
} from "@/api/client";
import { TTS_VOICES, type SpeechCommand } from "@/api/types";
import { SpeakButton } from "@/components/SpeakButton";
import { VoiceInputButton } from "@/components/VoiceInputButton";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useSpeechMode } from "@/context/SpeechModeContext";
import { useSpeechSettings } from "@/context/SpeechSettingsContext";
import { ACTION_LABELS, describeAction } from "@/lib/speechActions";
import { MESSAGE_HOLD_MS } from "@/lib/speechTiming";

const ACTIONS = Object.keys(ACTION_LABELS);
const COMMAND_LANGUAGES = ["en", "ru"];

export function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get("tab") ?? "tts";

  return (
    <div className="flex flex-col gap-6">
      <Card className="relative py-4">
        <Button
          asChild
          variant="ghost"
          size="icon-sm"
          aria-label="Справка о синтезе и распознавании речи"
          className="absolute top-3 right-3 text-muted-foreground"
        >
          <Link to="/help#speech">
            <HelpCircle className="size-4" />
          </Link>
        </Button>
        <CardHeader>
          <CardTitle>Настройки</CardTitle>
          <CardDescription>
            Синтез и распознавание речи — оба полностью локально (Piper и faster-whisper), выбор
            голоса, темпа и громкости, а также список голосовых команд, на которые реагирует
            система.
          </CardDescription>
        </CardHeader>
      </Card>

      <Tabs
        value={activeTab}
        onValueChange={(value) => setSearchParams({ tab: value }, { replace: true })}
      >
        <TabsList>
          <TabsTrigger value="tts">Синтез речи</TabsTrigger>
          <TabsTrigger value="stt">Распознавание речи</TabsTrigger>
          <TabsTrigger value="commands">Команды</TabsTrigger>
        </TabsList>
        <TabsContent value="tts">
          <TtsSettingsTab />
        </TabsContent>
        <TabsContent value="stt">
          <SttSettingsTab />
        </TabsContent>
        <TabsContent value="commands">
          <CommandsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function TtsSettingsTab() {
  const { voice, rate, volume, update } = useSpeechSettings();
  const [testText, setTestText] = useState(
    "Пример текста для проверки синтеза речи.",
  );

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 pt-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label>Голос</Label>
            <Select value={voice} onValueChange={(value) => update({ voice: value })}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TTS_VOICES.map((v) => (
                  <SelectItem key={v.value} value={v.value}>
                    {v.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <Label>Темп</Label>
              <span className="text-xs text-muted-foreground">{rate.toFixed(1)}×</span>
            </div>
            <Slider
              min={0.5}
              max={2}
              step={0.1}
              value={[rate]}
              onValueChange={([value]) => update({ rate: value })}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <Label>Громкость</Label>
              <span className="text-xs text-muted-foreground">{Math.round(volume * 100)}%</span>
            </div>
            <Slider
              min={0}
              max={1}
              step={0.05}
              value={[volume]}
              onValueChange={([value]) => update({ volume: value })}
            />
          </div>
        </div>

        <div className="flex flex-col gap-1.5 border-t pt-4">
          <Label>Проверка</Label>
          <Textarea
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            className="h-24"
          />
          <div className="flex justify-end">
            <SpeakButton text={testText} size="sm" variant="secondary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SttSettingsTab() {
  const { sttLanguage, activationPhrase, update } = useSpeechSettings();
  const [transcript, setTranscript] = useState("");
  const [phraseDraft, setPhraseDraft] = useState(activationPhrase);
  const [justApplied, setJustApplied] = useState(false);
  const isDirty = phraseDraft.trim() !== activationPhrase;

  useEffect(() => {
    setPhraseDraft(activationPhrase);
  }, [activationPhrase]);

  useEffect(() => {
    if (!justApplied) return;
    const timeout = setTimeout(() => setJustApplied(false), MESSAGE_HOLD_MS);
    return () => clearTimeout(timeout);
  }, [justApplied]);

  function applyPhrase() {
    update({ activationPhrase: phraseDraft.trim() });
    setJustApplied(true);
  }

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 pt-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label>Естественный язык (ЕЯ)</Label>
            <Select value={sttLanguage} onValueChange={(value) => update({ sttLanguage: value })}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="en">Английский</SelectItem>
                <SelectItem value="ru">Русский</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="flex flex-col gap-1.5 border-t pt-4">
          <Label htmlFor="activation-phrase">Фраза активации голосового режима</Label>
          <p className="text-xs text-muted-foreground">
            Если задана, ассистент реагирует на команды только после этой фразы (например, «Ассистент,
            найди кошек»). Оставьте пустым, чтобы реагировать на любую распознанную фразу, как сейчас.
          </p>
          <div className="flex max-w-sm items-center gap-2">
            <Input
              id="activation-phrase"
              placeholder="например, ассистент"
              value={phraseDraft}
              onChange={(e) => setPhraseDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") applyPhrase();
              }}
            />
            <Button type="button" size="sm" variant="secondary" onClick={applyPhrase} disabled={!isDirty}>
              Применить
            </Button>
          </div>
          <p className="h-4 text-xs text-muted-foreground">
            {isDirty
              ? "Изменения не применены"
              : justApplied
                ? "Применено — уже действует в голосовом режиме"
                : null}
          </p>
        </div>

        <div className="flex flex-col gap-1.5 border-t pt-4">
          <Label>Проверка</Label>
          <p className="text-xs text-muted-foreground">
            Нажмите на микрофон и продиктуйте фразу — запись остановится сама после короткой паузы,
            либо нажмите на кнопку ещё раз, чтобы остановить её раньше.
          </p>
          <div className="flex items-center gap-3">
            <VoiceInputButton onTranscript={setTranscript} detectCommands={false} />
            <Textarea
              value={transcript}
              readOnly
              placeholder="Здесь появится распознанный текст…"
              className="h-20 flex-1"
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function CommandsTab() {
  const { refreshCommands } = useSpeechMode();
  const [commands, setCommands] = useState<SpeechCommand[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newPhrase, setNewPhrase] = useState("");
  const [newAction, setNewAction] = useState(ACTIONS[0]);
  const [newLanguage, setNewLanguage] = useState("en");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editPhrase, setEditPhrase] = useState("");
  const [editAction, setEditAction] = useState("");
  const [editLanguage, setEditLanguage] = useState("en");

  async function refresh() {
    setLoading(true);
    try {
      setCommands(await listSpeechCommands());
      refreshCommands();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function handleCreate() {
    if (!newPhrase.trim() || !newAction) return;
    try {
      await createSpeechCommand({ phrase: newPhrase.trim(), action: newAction, language: newLanguage });
      setNewPhrase("");
      setNewAction(ACTIONS[0]);
      setNewLanguage("en");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  function startEdit(command: SpeechCommand) {
    setEditingId(command.id);
    setEditPhrase(command.phrase);
    setEditAction(command.action);
    setEditLanguage(command.language);
  }

  async function handleSaveEdit(id: number) {
    try {
      await updateSpeechCommand(id, {
        phrase: editPhrase.trim(),
        action: editAction,
        language: editLanguage,
      });
      setEditingId(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleToggleActive(command: SpeechCommand) {
    try {
      await updateSpeechCommand(command.id, { is_active: !command.is_active });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteSpeechCommand(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <CardDescription>
        Список операций, на которые реагирует система распознавания речи: если распознанный
        текст содержит фразу-триггер, соответствующее действие выполняется автоматически, а
        пользователь получает уведомление.
      </CardDescription>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading ? (
        <div className="flex justify-center py-8 text-muted-foreground">
          <Loader2 className="size-5 animate-spin" />
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-center">Фраза</TableHead>
              <TableHead className="text-center">Действие</TableHead>
              <TableHead className="text-center">Язык</TableHead>
              <TableHead className="text-center">Активна</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {commands.map((command) => (
              <TableRow key={command.id}>
                {editingId === command.id ? (
                  <>
                    <TableCell>
                      <Input value={editPhrase} onChange={(e) => setEditPhrase(e.target.value)} />
                    </TableCell>
                    <TableCell>
                      <Select value={editAction} onValueChange={setEditAction}>
                        <SelectTrigger className="w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {ACTIONS.map((action) => (
                            <SelectItem key={action} value={action}>
                              {describeAction(action).label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell>
                      <Select value={editLanguage} onValueChange={setEditLanguage}>
                        <SelectTrigger className="w-full">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {COMMAND_LANGUAGES.map((lang) => (
                            <SelectItem key={lang} value={lang}>
                              {lang}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell />
                    <TableCell className="flex justify-end gap-2">
                      <Button size="sm" onClick={() => handleSaveEdit(command.id)}>
                        Сохранить
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>
                        Отмена
                      </Button>
                    </TableCell>
                  </>
                ) : (
                  <>
                    <TableCell className="text-center">{command.phrase}</TableCell>
                    <TableCell
                      className="text-center text-muted-foreground"
                      title={describeAction(command.action).hint}
                    >
                      {describeAction(command.action).label}
                    </TableCell>
                    <TableCell className="text-center text-muted-foreground">
                      {command.language}
                    </TableCell>
                    <TableCell className="text-center">
                      <button
                        type="button"
                        onClick={() => handleToggleActive(command)}
                        className={
                          command.is_active
                            ? "text-xs text-primary"
                            : "text-xs text-muted-foreground"
                        }
                      >
                        {command.is_active ? "да" : "нет"}
                      </button>
                    </TableCell>
                    <TableCell className="flex justify-end gap-1">
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        aria-label="Изменить"
                        onClick={() => startEdit(command)}
                      >
                        <Pencil className="size-3.5" />
                      </Button>
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        aria-label="Удалить"
                        onClick={() => handleDelete(command.id)}
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </TableCell>
                  </>
                )}
              </TableRow>
            ))}
            <TableRow>
              <TableCell>
                <Input
                  placeholder="например, «искать»"
                  value={newPhrase}
                  onChange={(e) => setNewPhrase(e.target.value)}
                />
              </TableCell>
              <TableCell>
                <Select value={newAction} onValueChange={setNewAction}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ACTIONS.map((action) => (
                      <SelectItem key={action} value={action}>
                        {describeAction(action).label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </TableCell>
              <TableCell>
                <Select value={newLanguage} onValueChange={setNewLanguage}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {COMMAND_LANGUAGES.map((lang) => (
                      <SelectItem key={lang} value={lang}>
                        {lang}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </TableCell>
              <TableCell />
              <TableCell className="flex justify-end">
                <Button size="sm" variant="secondary" onClick={handleCreate}>
                  <Plus className="size-3.5" />
                  Добавить
                </Button>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      )}
    </div>
  );
}
