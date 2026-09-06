import {
  BarChart3,
  Layers,
  Library,
  ListOrdered,
  Search,
  ThumbsUp,
  Waypoints,
} from "lucide-react";
import { useEffect, type ReactNode } from "react";
import { useLocation } from "react-router-dom";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

function Feature({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 rounded-md border p-3 transition-colors duration-150 hover:bg-accent/40">
      <span className="text-sm font-medium">{title}</span>
      <p className="text-sm text-muted-foreground">{children}</p>
    </div>
  );
}

function MetricEntry({
  id,
  title,
  formula,
  children,
}: {
  id: string;
  title: string;
  formula?: string;
  children: ReactNode;
}) {
  return (
    <div
      id={id}
      className="scroll-mt-24 rounded-md border p-3 transition-colors duration-150 target:border-primary target:bg-primary/5"
    >
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span className="text-sm font-medium">{title}</span>
        {formula && (
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground">{formula}</code>
        )}
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{children}</p>
    </div>
  );
}

/** A vertical, connected step-by-step narrative — for describing a process
 * (something that happens in order) rather than a flat set of independent
 * facts, which is what the plain Feature cards are for. */
function ProcessSteps({ steps }: { steps: { title: string; children: ReactNode }[] }) {
  return (
    <ol className="flex flex-col">
      {steps.map((step, i) => (
        <li key={i} className="relative flex gap-4 pb-6 last:pb-0">
          {i < steps.length - 1 && (
            <span
              aria-hidden
              className="absolute top-7 left-[13px] h-[calc(100%-1.25rem)] w-px bg-border"
            />
          )}
          <span className="relative z-10 flex size-7 shrink-0 items-center justify-center rounded-full border bg-background text-xs font-semibold">
            {i + 1}
          </span>
          <div className="flex flex-col gap-1 pt-0.5">
            <span className="text-sm font-medium">{step.title}</span>
            <p className="text-sm text-muted-foreground">{step.children}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

/** The ROMIP'2004 search-track methodology document (tasks/romip_metrics.pdf
 * in the repo, served statically from frontend/public) that every metric on
 * this page is drawn from — opens in a new tab so it doesn't navigate away
 * from the reference material you're currently reading. */
function RomipLink() {
  return (
    <a
      href="/romip_metrics.pdf"
      target="_blank"
      rel="noreferrer"
      className="text-primary underline-offset-2 hover:underline"
    >
      ROMIP&apos;2004
    </a>
  );
}

function Section({
  icon: Icon,
  title,
  description,
  id,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: ReactNode;
  id?: string;
  children: ReactNode;
}) {
  return (
    <Card id={id} className="scroll-mt-24 transition-shadow duration-200 hover:shadow-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Icon className="size-4" />
          </span>
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">{children}</CardContent>
    </Card>
  );
}

export function HelpPage() {
  const { hash } = useLocation();

  useEffect(() => {
    if (!hash) return;
    // The page scrolls inside a Radix ScrollArea viewport, not the window —
    // native scrollIntoView() has to guess which ancestor is "the" scroll
    // container, and on the very first paint (before the ScrollArea has
    // finished sizing its viewport) it sometimes guesses wrong or computes
    // against a not-yet-final layout, snapping the scroll position away
    // right after landing. Scrolling the viewport directly, after a paint,
    // sidesteps both problems. Instant rather than smooth: a smooth
    // scroll's animation can silently stall if the tab loses focus/
    // visibility right as it starts, leaving the page stuck at the top.
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

      <Section
        id="crawling"
        icon={Waypoints}
        title="Краулинг"
        description="Наполнение коллекции документами путём обхода веб-страниц по ссылкам."
      >
        <Feature title="Список адресов хранится в коллекции">
          Добавленные адреса сохраняются в базе данных вместе с коллекцией — их можно закрыть
          вкладку и вернуться позже, редактировать или удалять, не теряя настройки.
        </Feature>
        <Feature title="У каждого адреса свои настройки">
          Лимит документов, глубина обхода и ограничение по домену задаются отдельно для каждого
          адреса — они независимы: один адрес может обходиться на глубину 3, другой — только
          собирать саму страницу.
        </Feature>
        <Feature title="Только этот домен">
          Включите переключатель у адреса, чтобы обход не уходил на другие домены и поддомены
          (например, с en.example.com на example.com или на внешние ссылки) — полезно для сайтов
          с языковыми поддоменами или большим числом внешних ссылок.
        </Feature>
        <Feature title="Запуск краулинга пересобирает коллекцию">
          «Запустить краулинг» удаляет все текущие документы коллекции и построенный по ним индекс,
          затем заново обходит все настроенные адреса — результат никогда не смешивает старые и
          новые данные.
        </Feature>
        <Feature title="Прогресс в реальном времени">
          Каждый адрес обходится отдельной задачей; пока задача выполняется, страница показывает
          счётчики (найдено/обработано/ошибок) через WebSocket, с откатом на опрос сервера, если
          соединение недоступно.
        </Feature>
        <Feature title="Прерывание">
          Кнопка «Прервать» на карточке задачи останавливает обход в течение нескольких секунд —
          уже сохранённые документы остаются в коллекции, задача помечается как «отменён».
        </Feature>
      </Section>

      <Section
        id="collections"
        icon={Library}
        title="Коллекции"
        description="Управление коллекциями документов: полный CRUD, загрузка файлов, переиндексация."
      >
        <Feature title="Документы: создание, правка, удаление">
          На вкладке доступен полный CRUD — можно добавить документ вручную, отредактировать
          заголовок/текст/адрес источника или удалить документ из коллекции.
        </Feature>
        <Feature title="Загрузка HTML-файлов">
          При добавлении документа можно загрузить готовый .html файл — текст и заголовок
          извлекаются из него автоматически прямо в браузере.
        </Feature>
        <Feature title="Обновление коллекции">
          Документы с известным URL можно перезагрузить одной кнопкой — их содержимое будет
          заново получено с исходного адреса без создания дубликатов.
        </Feature>
        <Feature title="Индекс устарел">
          Если документы менялись после последней индексации, коллекция помечается как
          «индекс устарел» — предупреждение видно и здесь, и на странице поиска.
        </Feature>
        <Feature title="Прерывание индексации и обновления">
          Пока идёт построение индекса или обновление документов по URL, рядом с прогрессом
          доступна кнопка «Прервать» — задача останавливается в течение нескольких секунд, а уже
          обработанные документы/термины не откатываются.
        </Feature>
      </Section>

      <Section
        id="searching"
        icon={Search}
        title="Поиск"
        description="Запрос сравнивается с документами коллекции и ранжируется по сходству — модель поиска выбирается отдельно (см. «Модели поиска» ниже)."
      >
        <Feature title="Карточка результата">
          Слева сверху — номер и заголовок, справа — оценка сходства и дата документа. Внизу
          слева — источник (иконка глобуса и ссылка), в центре — сокращённый фрагмент текста с
          подсветкой слов запроса.
        </Feature>
        <Feature title="Разворачивание карточки">
          Кнопка «Показать полностью» раскрывает карточку: полный текст документа в прокручиваемой
          области и список терминов, совпавших с запросом.
        </Feature>
        <Feature title="Режим разметки">
          Включается переключателем над списком результатов. В этом режиме в правом нижнем углу
          каждой карточки становится активна кнопка{" "}
          <ThumbsUp className="inline size-3.5 align-text-bottom" /> — отмечает документ как
          релевантный запросу и подсвечивается зелёным. Отдельной кнопки «нерелевантен» нет: по
          методике ROMIP всё, что не отмечено релевантным, при подсчёте метрик и так считается
          нерелевантным, так что вторая отметка ничего бы не меняла. Повторное нажатие снимает
          отметку. Карточка при этом не меняет размер.
        </Feature>
        <Feature title="Эталонная разметка (qrels)">
          Отмеченные лайком документы сохраняются как эталонная разметка запроса и используются
          для расчёта метрик качества на вкладке «Метрики». Повторный поиск по тому же тексту
          запроса — та же разметка: отметки накапливаются, а не начинаются заново.
        </Feature>
        <Feature title="Разметка вне выдачи">
          В режиме разметки под результатами есть кнопка «Проверить остальные документы
          коллекции» — список всех документов коллекции, которых нет в текущей выдаче. Отмечая
          там документы как релевантные, вы расширяете эталонную разметку за пределы того, что
          поиск вообще нашёл — это и делает Recall содержательной метрикой.
        </Feature>
      </Section>

      <Section
        id="search-models"
        icon={Layers}
        title="Модели поиска"
        description="Два независимых способа ранжирования — можно сравнивать их метрики бок о бок."
      >
        <Feature title="TF-IDF + косинусная мера">
          Классическая векторная модель: запрос и документы раскладываются на термины,
          взвешиваются по TF-IDF и сравниваются косинусной мерой. Быстро, объяснимо — карточки
          результатов показывают, какие именно термины запроса совпали с документом.
        </Feature>
        <Feature title="Qwen3 Embedding 8B (эмбеддинги)">
          Семантическая модель: документ и запрос кодируются в плотные векторы (4096 чисел) через
          OpenRouter, учитывающие смысл текста, а не только совпадение слов — поэтому находит
          документы на других языках или без общей лексики с запросом. Контекст модели — 32 000
          токенов, но длинные документы при индексации всё равно разбиваются на перекрывающиеся
          фрагменты (чанки) — каждый кодируется отдельно, а результатом документа становится его
          лучший по сходству
          фрагмент. Так ни один фрагмент длинного документа не теряется. У таких результатов нет
          списка «совпавших терминов» — это не про буквальное совпадение слов.
        </Feature>
        <Feature title="Общая разметка релевантности">
          Лайки, проставленные для запроса на странице «Поиск», используются при подсчёте метрик
          для любой модели — разметку достаточно сделать один раз, независимо от того, какой
          моделью её проставили. Стоит проверить «Проверить остальные документы коллекции» под
          обеими моделями: у них разные топ-выдачи, и документ, который одна модель не показала бы
          вовсе, не будет размечен, если оценивать только видимые карточки.
        </Feature>
        <Feature title="Сравнение на странице «Метрики»">
          Отметьте нужные модели чекбоксами вверху страницы — таблицы и графики построятся сразу
          для всех выбранных, с общим цветом для каждой модели. Если по какому-то запросу ещё нет
          результата под одной из моделей, она просто не отображается в этой части сравнения — это
          не то же самое, что нулевая оценка.
        </Feature>
      </Section>

      <Section
        id="metrics"
        icon={BarChart3}
        title="Метрики качества"
        description={
          <>
            Как считается качество ранжирования — методика <RomipLink />, дорожка поиска.
          </>
        }
      >
        <ProcessSteps
          steps={[
            {
              title: "Поиск сохраняет полное ранжирование",
              children:
                "Каждый поиск ранжирует всю коллекцию по сходству с запросом и сохраняет этот список целиком, а не только те несколько документов, что показаны на экране. Число результатов (Топ-K) в поле поиска влияет только на то, что видно, а не на то, что участвует в расчёте метрик.",
            },
            {
              title: "Вы отмечаете релевантность",
              children:
                "На странице «Поиск», в режиме разметки, отмечайте лайком найденные релевантные документы. Для документов, которых поиск не показал, — кнопка «Проверить остальные документы коллекции».",
            },
            {
              title: "Метрики по запросу",
              children:
                "Precision, Recall, F1, Precision(5)/Precision(10), R-Precision, Average Precision и 11-точечная кривая — считаются по сохранённому полному ранжированию и текущей разметке.",
            },
            {
              title: "Метрики по коллекции",
              children:
                "Каждый размеченный запрос вносит вклад в сводку: MAP и средние R-Precision/P@5/P@10 — среднее по всем размеченным запросам коллекции.",
            },
          ]}
        />

        <div className="grid gap-3 sm:grid-cols-2">
          <MetricEntry id="metric-precision-recall" title="Precision и Recall" formula="p = a/(a+b), r = a/(a+c)">
            Precision — доля релевантных документов среди найденных; Recall — доля найденных из
            всех релевантных документов коллекции (<RomipLink />, п. 1.1.1–1.1.2). Здесь обе
            считаются по всему сохранённому ранжированию.
          </MetricEntry>

          <MetricEntry id="metric-f1" title="F-мера" formula="F = 2 / (1/p + 1/r)">
            Гармоническое среднее Precision и Recall — единая величина, близкая к нулю, если хотя
            бы одна из двух метрик мала. В методике описана для дорожки классификации (п. 1.1.5);
            здесь приведена как привычное дополнение рядом с Precision и Recall.
          </MetricEntry>

          <MetricEntry
            id="metric-precision-at-n"
            title="Precision(5) и Precision(10)"
            formula="p(n) = релевантных среди первых n / n"
          >
            Точность на первых n документах выдачи — при n = 5 и n = 10 (п. 1.3.1). Показывает,
            насколько полезной оказалась бы первая страница результатов.
          </MetricEntry>

          <MetricEntry
            id="metric-r-precision"
            title="R-Precision"
            formula="R-Precision = p(n), n = число релевантных документов запроса"
          >
            То же самое Precision(n), но отсечка n своя для каждого запроса — равна числу его
            релевантных документов (п. 1.3.2). У идеального ранжирования R-Precision всегда равна
            1, поэтому метрику можно сравнивать между запросами с разным числом релевантных
            документов.
          </MetricEntry>

          <MetricEntry id="metric-ap" title="Average Precision (AP)" formula="AP = (1/k) · Σ p(pos(i))">
            Среднее значение Precision в момент нахождения каждого из k релевантных документов —
            чем выше в списке они стоят, тем выше AP (п. 1.3.3); документ, которого нет в
            ранжировании вовсе, даёт слагаемое 0. MAP на странице «Метрики» — среднее AP по всем
            размеченным запросам коллекции.
          </MetricEntry>

          <MetricEntry id="metric-curve" title="11-точечная кривая Precision/Recall">
            Precision как функция Recall на 11 фиксированных уровнях (0.0, 0.1, …, 1.0): для
            каждого уровня берётся максимальная точность среди точек ранжирования, где полнота
            достигла этого уровня или превысила его (п. 1.3.4, вариант TREC), затем усредняется по
            размеченным запросам. Методика описывает и модифицированный вариант такой кривой
            (RIRES) — здесь построен классический, TREC.
          </MetricEntry>
        </div>

        <MetricEntry id="metric-qrels-scope" title="Запросы без релевантных документов">
          Если для запроса не отмечено ни одного релевантного документа, он не попадает в
          сводку — при нуле релевантных документов Precision, Recall и AP превращаются в
          неопределённость вида 0/0 (п. 1).
        </MetricEntry>
      </Section>
    </div>
  );
}
