FROM python:3.11-slim@sha256:a3ab0b966bc4e91546a033e22093cb840908979487a9fc0e6e38295747e49ac0

# Reproducible build identity — passed by the build script as --build-arg.
# Default is 0 (Unix epoch) so the image is safe to build without the argument.
# Tools that respect SOURCE_DATE_EPOCH (pip >= 21.3, adduser) will use this
# value for any timestamps they write into the layer filesystem.
ARG SOURCE_DATE_EPOCH=0
ENV SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}

LABEL org.opencontainers.image.title="Keyhole Test Runtime" \
      org.opencontainers.image.description="Public test runtime for the Keyhole developer ecosystem" \
      org.opencontainers.image.source="https://github.com/keyhole-solution/keyhole-developer-kit"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RUNTIME_VERSION=0.1.0 \
    RUNTIME_ENVIRONMENT=dev \
    # MCP Governance Bridge — set these to connect to the Keyhole governance controller.
    # Without them the runtime operates in local-only mode (no governance gate).
    KEYHOLE_MCP_URL="" \
    KEYHOLE_MCP_TOKEN="" \
    KEYHOLE_MCP_RUN_TYPE="convergence.status.v0_1" \
    KEYHOLE_MCP_TIMEOUT="10"

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
