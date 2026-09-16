import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { CollectionProvider } from "./context/CollectionContext";
import { SearchModelProvider } from "./context/SearchModelContext";
import { SpeechModeProvider } from "./context/SpeechModeContext";
import { SpeechPlaybackProvider } from "./context/SpeechPlaybackContext";
import { SpeechSettingsProvider } from "./context/SpeechSettingsContext";
import { CollectionsPage } from "./pages/CollectionsPage";
import { CrawlPage } from "./pages/CrawlPage";
import { HelpPage } from "./pages/HelpPage";
import { LanguageIdPage } from "./pages/LanguageIdPage";
import { MetricsPage } from "./pages/MetricsPage";
import { SearchPage } from "./pages/SearchPage";
import { SentenceSyntaxReportPage } from "./pages/SentenceSyntaxReportPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SummarizationPage } from "./pages/SummarizationPage";
import { TranslationPage } from "./pages/TranslationPage";

export default function App() {
  return (
    <CollectionProvider>
      <SearchModelProvider>
        <SpeechSettingsProvider>
          <SpeechPlaybackProvider>
            <SpeechModeProvider>
              <Routes>
                <Route element={<Layout />}>
                  <Route path="/" element={<Navigate to="/crawl" replace />} />
                  <Route path="/crawl" element={<CrawlPage />} />
                  <Route path="/collections" element={<CollectionsPage />} />
                  <Route path="/search" element={<SearchPage />} />
                  <Route path="/metrics" element={<MetricsPage />} />
                  <Route path="/lang-id" element={<LanguageIdPage />} />
                  <Route path="/summarization" element={<SummarizationPage />} />
                  <Route path="/translation" element={<TranslationPage />} />
                  <Route
                    path="/translation/runs/:runId/sentences/:sentenceIndex"
                    element={<SentenceSyntaxReportPage />}
                  />
                  <Route path="/settings" element={<SettingsPage />} />
                  <Route path="/help" element={<HelpPage />} />
                </Route>
              </Routes>
            </SpeechModeProvider>
          </SpeechPlaybackProvider>
        </SpeechSettingsProvider>
      </SearchModelProvider>
    </CollectionProvider>
  );
}
