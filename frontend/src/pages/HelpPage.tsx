import {
  BarChart3,
  FileText,
  Library,
  Search,
  ThumbsDown,
  ThumbsUp,
  Waypoints,
} from "lucide-react";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

function Feature({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 rounded-md border p-3 transition-colors duration-150 hover:bg-accent/40">
      <span className="text-sm font-medium">{title}</span>
      <p className="text-sm text-muted-foreground">{children}</p>
    </div>
  );
}

function Section({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Card className="transition-shadow duration-200 hover:shadow-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Icon className="size-4" />
          </span>
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">{children}</CardContent>
    </Card>
  );
}

export function HelpPage() {
  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Справка</CardTitle>
          <CardDescription>
            Информационно-поисковая система: векторная модель (TF-IDF + косинусная мера),
            построена вокруг четырёх этапов работы — краулинг источников, управление коллекциями
            документов, поиск с оценкой релевантности и расчёт метрик качества (ROMIP&apos;2004).
          </CardDescription>
        </CardHeader>
      </Card>

      <Section
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
      </Section>

      <Section
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
      </Section>

      <Section
        icon={Search}
        title="Поиск"
        description="Векторная модель: запрос и документы — TF-IDF векторы, ранжирование по косинусной мере."
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
          Включается переключателем над списком результатов. В этом режиме становятся активны
          кнопки-иконки {" "}
          <ThumbsUp className="inline size-3.5 align-text-bottom" /> /{" "}
          <ThumbsDown className="inline size-3.5 align-text-bottom" /> в правом нижнем углу
          каждой карточки — выбранная подсвечивается зелёным (релевантен) или красным
          (нерелевантен). Карточка при этом не меняет размер.
        </Feature>
        <Feature title="Эталонная разметка (qrels)">
          Проставленные оценки релевантности сохраняются как эталонная разметка запроса и
          используются для расчёта метрик качества на вкладке «Метрики».
        </Feature>
      </Section>

      <Section
        icon={BarChart3}
        title="Метрики качества"
        description="Официальная методика ROMIP'2004 (дорожка поиска) — считается по размеченным запросам."
      >
        <Feature title="По каждому запросу">
          Precision, Recall, F1 (по всему списку найденного), Precision(5) и Precision(10)
          (точность на первых 5/10 документах), Average Precision, R-Precision и 11-точечная
          интерполированная кривая Precision/Recall.
        </Feature>
        <Feature title="По коллекции">
          MAP — среднее Average Precision по всем размеченным запросам (макроусреднение);
          Precision/Recall/F1 коллекции — микроусреднение (суммирование по всем запросам, затем
          деление), как того требует методика ROMIP.
        </Feature>
        <Feature title="Запросы без релевантных документов">
          Запросы, для которых не отмечено ни одного релевантного документа, исключаются из
          расчёта агрегатов — как предписывает методика.
        </Feature>
        <Feature title="Визуализация">
          Сводные показатели, усреднённая P/R-кривая, сравнение Average Precision между запросами
          и подробная таблица метрик по каждому запросу.
        </Feature>
      </Section>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="size-4" />
            Типичный порядок действий
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="flex flex-col gap-2 text-sm">
            <li className="flex items-center gap-2">
              <Badge variant="secondary" className="shrink-0">1</Badge>
              Создайте коллекцию и запустите краулинг с одного или нескольких стартовых адресов.
            </li>
            <li className="flex items-center gap-2">
              <Badge variant="secondary" className="shrink-0">2</Badge>
              При необходимости отредактируйте документы или добавьте свои HTML-файлы на вкладке
              «Коллекции», затем постройте индекс.
            </li>
            <li className="flex items-center gap-2">
              <Badge variant="secondary" className="shrink-0">3</Badge>
              Выполните поисковые запросы и, включив режим разметки, отметьте релевантные и
              нерелевантные документы.
            </li>
            <li className="flex items-center gap-2">
              <Badge variant="secondary" className="shrink-0">4</Badge>
              Оцените качество поиска на вкладке «Метрики».
            </li>
          </ol>
        </CardContent>
      </Card>
    </div>
  );
}
