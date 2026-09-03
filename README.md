# Информационно-поисковая система (ЛР1, вариант 22)

Векторная модель поиска (TF‑IDF + косинусная мера) по англоязычной веб-коллекции,
собираемой собственным краулером, с оценкой качества по метрикам ROMIP.
Архитектура и план — см. [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) и
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Состав

| Путь | Что это |
|---|---|
| `packages/nlp_core` | Переиспользуемая NLP-библиотека: токенизация, TF‑IDF, косинус, метрики качества поиска |
| `services/api` | FastAPI-гейтвей: коллекции, документы, краулинг, поиск, метрики |
| `services/nlp-service` | HTTP-обёртка над `nlp_core` |
| `services/crawler-service` | Воркер обхода веб-страниц (BFS, лимит документов/глубины) |
| `frontend` | React + Vite + TypeScript UI |

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- API: http://localhost:8000/docs
- nlp-service: http://localhost:8001/docs
- Adminer (просмотр БД): http://localhost:8080

## Разработка

```bash
# nlp_core
cd packages/nlp_core && pip install -e ".[dev]" && pytest

# api
cd services/api && pip install -r requirements.txt && pytest
```

## Дополнительные требования

- добавить возможность создания задачи на автоматический кроулинг в админ-панели
