FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY packages/nlp_core ./packages/nlp_core
COPY services/lang-id-service/requirements.txt ./requirements.txt
# CPU-only torch wheel — inference is a single forward pass and training is
# a few hundred epochs over a few hundred 4096-dim vectors, so no GPU is
# needed and the CUDA wheel would only bloat the image.
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

COPY services/lang-id-service/app ./app

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
