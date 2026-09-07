FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# pip's default 15s read timeout is too aggressive for large wheel downloads
# (e.g. this service's transitive deps) on a slow or congested connection —
# this only widens the timeout pip itself already retries against.
ENV PIP_DEFAULT_TIMEOUT=180

COPY packages/ips_db ./packages/ips_db
COPY packages/nlp_core ./packages/nlp_core
COPY services/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/api/app ./app
COPY services/api/alembic.ini ./alembic.ini
COPY services/api/migrations ./migrations

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
