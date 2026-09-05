import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { CollectionProvider } from "./context/CollectionContext";
import { SearchModelProvider } from "./context/SearchModelContext";
import { CollectionsPage } from "./pages/CollectionsPage";
import { CrawlPage } from "./pages/CrawlPage";
import { HelpPage } from "./pages/HelpPage";
import { MetricsPage } from "./pages/MetricsPage";
import { SearchPage } from "./pages/SearchPage";

export default function App() {
  return (
    <CollectionProvider>
      <SearchModelProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/crawl" replace />} />
            <Route path="/crawl" element={<CrawlPage />} />
            <Route path="/collections" element={<CollectionsPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/metrics" element={<MetricsPage />} />
            <Route path="/help" element={<HelpPage />} />
          </Route>
        </Routes>
      </SearchModelProvider>
    </CollectionProvider>
  );
}
