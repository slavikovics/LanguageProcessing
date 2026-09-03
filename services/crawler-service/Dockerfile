FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY packages/ips_db ./packages/ips_db
COPY packages/nlp_core ./packages/nlp_core
COPY services/crawler-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/crawler-service/app ./app

CMD ["python", "-m", "app.main"]
