FROM python:3.11-slim

LABEL org.opencontainers.image.title="Keyhole Test Runtime" \
      org.opencontainers.image.description="Public test runtime for the Keyhole developer ecosystem" \
      org.opencontainers.image.source="https://github.com/keyhole-solution/keyhole-developer-kit"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RUNTIME_VERSION=0.1.0 \
    RUNTIME_ENVIRONMENT=production

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

RUN addgroup --system runtime && adduser --system --ingroup runtime runtime
USER runtime

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
