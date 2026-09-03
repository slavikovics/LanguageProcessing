import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { CollectionsPage } from "./pages/CollectionsPage";
import { CrawlPage } from "./pages/CrawlPage";
import { MetricsPage } from "./pages/MetricsPage";
import { SearchPage } from "./pages/SearchPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/crawl" replace />} />
        <Route path="/crawl" element={<CrawlPage />} />
        <Route path="/collections" element={<CollectionsPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/metrics" element={<MetricsPage />} />
      </Route>
    </Routes>
  );
}
