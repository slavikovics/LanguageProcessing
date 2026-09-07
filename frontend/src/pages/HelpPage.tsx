import { ListOrdered } from "lucide-react";
import { useEffect } from "react";
import { useLocation } from "react-router-dom";

import { CollectionsHelp } from "@/components/help/CollectionsHelp";
import { ProcessSteps, RomipLink } from "@/components/help/HelpBlocks";
import { CrawlingHelp } from "@/components/help/CrawlingHelp";
import { LangIdHelp } from "@/components/help/LangIdHelp";
import { MetricsHelp } from "@/components/help/MetricsHelp";
import { SearchingHelp } from "@/components/help/SearchingHelp";
import { SearchModelsHelp } from "@/components/help/SearchModelsHelp";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function HelpPage() {
  const { hash } = useLocation();

  useEffect(() => {
    if (!hash) return;
    // Scrolls the Radix ScrollArea viewport directly, after a paint — native
    // scrollIntoView() guesses the wrong ancestor before the viewport has
    // finished sizing. Instant, not smooth: a smooth scroll can stall if the
    // tab loses focus right as it starts.
    const id = hash.slice(1);
    const raf = requestAnimationFrame(() => {
      const target = document.getElementById(id);
      if (!target) return;
      const viewport = target.closest<HTMLElement>('[data-slot="scroll-area-viewport"]');
      if (!viewport) {
        target.scrollIntoView({ behavior: "instant", block: "start" });
        return;
      }
      const scrollMarginTop = parseFloat(getComputedStyle(target).scrollMarginTop) || 0;
      const targetTop =
        target.getBoundingClientRect().top - viewport.getBoundingClientRect().top + viewport.scrollTop;
      viewport.scrollTo({ top: targetTop - scrollMarginTop, behavior: "instant" });
    });
    return () => cancelAnimationFrame(raf);
  }, [hash]);

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Справка</CardTitle>
          <CardDescription>
            Информационно-поисковая система с двумя независимыми моделями поиска — TF-IDF с
            косинусной мерой и семантические эмбеддинги, — построена вокруг четырёх этапов работы:
            краулинг источников, управление коллекциями документов, поиск с оценкой релевантности и
            расчёт метрик качества (<RomipLink />).
          </CardDescription>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListOrdered className="size-4" />
            Типичный порядок действий
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ProcessSteps
            steps={[
              {
                title: "Соберите коллекцию",
                children: "Создайте коллекцию и запустите краулинг с одного или нескольких стартовых адресов.",
              },
              {
                title: "Приведите документы в порядок",
                children:
                  "При необходимости отредактируйте документы или добавьте свои HTML-файлы на вкладке «Коллекции», затем постройте индекс.",
              },
              {
                title: "Найдите и разметьте",
                children:
                  "Выполните поисковые запросы и, включив режим разметки, отметьте лайком найденные релевантные документы.",
              },
              {
                title: "Оцените качество",
                children: "Оцените качество поиска на вкладке «Метрики».",
              },
            ]}
          />
        </CardContent>
      </Card>

      <CrawlingHelp />
      <CollectionsHelp />
      <SearchingHelp />
      <SearchModelsHelp />
      <MetricsHelp />
      <LangIdHelp />
    </div>
  );
}
