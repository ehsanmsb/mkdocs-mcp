# syntax=docker/dockerfile:1
# ---- builder -------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
# Build a wheel and install it (+ deps) into an isolated prefix.
RUN uv pip install --system --prefix /install .

# ---- runtime -------------------------------------------------------------
FROM python:3.12-slim AS runtime

# git is required by the git source adapter.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/install/bin:$PATH \
    PYTHONPATH=/install/lib/python3.12/site-packages \
    MKDOCS_MCP_HOST=0.0.0.0 \
    MKDOCS_MCP_PORT=8000 \
    MKDOCS_MCP_REPO_DIR=/data/repo \
    MKDOCS_MCP_SNAPSHOT_PATH=/data/index-snapshot.json

COPY --from=builder /install /install

# OpenShift runs with an arbitrary non-root UID; /data must be group-writable.
RUN mkdir -p /data && chgrp -R 0 /data && chmod -R g=u /data
WORKDIR /data
USER 1001

EXPOSE 8000 9000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

ENTRYPOINT ["mkdocs-mcp"]
