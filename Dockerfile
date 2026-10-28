# syntax=docker/dockerfile:1.7
# Multi-stage build. The runtime image carries only the installed package, the
# web assets and the dataset, with no build tooling, no tests and no dev deps,
# and runs as an unprivileged user. "One command, clean machine, no API key, no
# cloud account" is the whole promise, so the image has to honour it.

# ---- build ------------------------------------------------------------------
FROM python:3.12-slim AS build
WORKDIR /build

COPY pyproject.toml requirements.txt ./
COPY src ./src
RUN python -m pip install --no-cache-dir --upgrade pip build \
 && python -m pip install --no-cache-dir -r requirements.txt \
 && python -m build --wheel --outdir /dist

# ---- runtime ----------------------------------------------------------------
FROM python:3.12-slim AS runtime

# No pyc, unbuffered logs, no pip cache.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SHOMER_HOST=0.0.0.0 \
    PORT=8080

RUN useradd --create-home --uid 10001 shomer
WORKDIR /app

COPY --from=build /dist/*.whl /tmp/
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
 && python -m pip install --no-cache-dir /tmp/*.whl \
 && rm -rf /tmp/*.whl

# Runtime assets the app serves and measures against.
COPY web ./web
COPY data/ground_truth.json ./data/ground_truth.json

USER shomer
EXPOSE 8080

# Liveness: the health route also reports ledger integrity. Reads $PORT so it
# stays correct when a platform injects a different port.
HEALTHCHECK --interval=30s --timeout=4s --start-period=5s --retries=3 \
  CMD python -c "import os,urllib.request,sys; p=os.environ.get('PORT','8080'); sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{p}/api/health').status==200 else 1)"

# uvicorn serves the API and the static console from the same origin. Shell form
# so ${PORT} expands: the platform injects it, the default covers local runs.
CMD ["sh", "-c", "python -m uvicorn shomer_gate.api.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
