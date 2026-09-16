FROM python:3.12-slim

WORKDIR /app

ENV PIP_DEFAULT_TIMEOUT=180

COPY services/speech-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m piper.download_voices en_US-amy-medium en_US-ryan-medium --download-dir /app/piper-voices

COPY services/speech-service/app ./app

EXPOSE 8004

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
