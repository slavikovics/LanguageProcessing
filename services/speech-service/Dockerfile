FROM python:3.12-slim

WORKDIR /app

ENV PIP_DEFAULT_TIMEOUT=180

COPY services/speech-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m piper.download_voices \
        en_US-amy-medium en_US-ryan-medium en_US-lessac-medium \
        en_US-hfc_female-medium en_US-hfc_male-medium en_US-kristin-medium en_US-joe-medium \
        en_GB-alba-medium en_GB-jenny_dioco-medium en_GB-alan-medium \
        --download-dir /app/piper-voices

COPY services/speech-service/app ./app

EXPOSE 8004

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
