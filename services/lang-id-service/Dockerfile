FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Kept byte-for-byte identical to services/mt-service/Dockerfile's torch
# install step so Docker's build cache reuses this layer (weights already
# downloaded) instead of fetching the ~200MB CPU wheel again for that
# service. If this line changes, update the other Dockerfile too.
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    "numpy<2" torch==2.5.1

COPY packages/nlp_core ./packages/nlp_core
COPY services/lang-id-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

COPY services/lang-id-service/app ./app

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
