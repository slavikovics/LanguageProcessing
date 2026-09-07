import { useCallback, useEffect, useState } from "react";
import { buildAlphabeticProfile, buildFrequentWordsProfile, listLangIdProfiles } from "../api/client";
import { LANG_ID_LANGUAGES, LANG_ID_METHOD_LABELS, type LangIdProfile } from "../api/types";

import { NeuralTrainingPanel } from "@/components/NeuralTrainingPanel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function LangIdProfilesTab() {
  const [profiles, setProfiles] = useState<LangIdProfile[]>([]);
  const refreshProfiles = useCallback(async () => {
    setProfiles(await listLangIdProfiles());
  }, []);
  useEffect(() => {
    void refreshProfiles();
  }, [refreshProfiles]);

  const [buildingKey, setBuildingKey] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);

  async function handleBuildLexicalProfile(method: "frequent_words" | "alphabetic", language: string) {
    setBuildingKey(`${method}:${language}`);
    setProfileError(null);
    try {
      if (method === "frequent_words") await buildFrequentWordsProfile(language);
      else await buildAlphabeticProfile(language);
      await refreshProfiles();
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : String(err));
    } finally {
      setBuildingKey(null);
    }
  }

  const neuralProfile = profiles.find((p) => p.method === "neural");
  const lexicalProfile = (method: "frequent_words" | "alphabetic", language: string) =>
    profiles.find((p) => p.method === method && p.language === language);

  return (
    <div className="flex flex-col gap-4">
      {(["frequent_words", "alphabetic"] as const).map((method) => (
        <Card key={method}>
          <CardHeader>
            <CardTitle>{LANG_ID_METHOD_LABELS[method]}</CardTitle>
            <CardDescription>Профиль строится по всем документам обучающей выборки, размеченным этим языком.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap justify-center gap-3">
            {LANG_ID_LANGUAGES.map((lang) => {
              const profile = lexicalProfile(method, lang.code);
              const key = `${method}:${lang.code}`;
              return (
                <div key={lang.code} className="flex flex-col gap-2 rounded-md border p-3">
                  <span className="text-sm font-medium">{lang.label}</span>
                  <span className="text-xs text-muted-foreground">
                    {profile
                      ? `${profile.source_document_count} документов · ${new Date(profile.built_at).toLocaleString()}`
                      : "Профиль не построен"}
                  </span>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={buildingKey === key}
                    onClick={() => handleBuildLexicalProfile(method, lang.code)}
                  >
                    {buildingKey === key ? "Строим…" : "Построить"}
                  </Button>
                </div>
              );
            })}
          </CardContent>
        </Card>
      ))}
      <NeuralTrainingPanel profile={neuralProfile} onTrained={refreshProfiles} />
      {profileError && <p className="text-sm text-destructive">{profileError}</p>}
    </div>
  );
}
