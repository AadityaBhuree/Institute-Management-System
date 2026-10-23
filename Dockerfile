# ==============================================================================
# Institute Management System (IMS Enterprise) - Production Dockerfile
# Multi-stage, non-root, hardened Python 3.11-slim container with SQLite WAL support
# ==============================================================================

FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final Runtime Image
FROM python:3.11-slim AS runtime

# System runtime dependencies & security tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed wheels from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    IMS_DB_PATH=/app/data/ims.db

# Create non-root unprivileged service account
RUN groupadd -g 10001 imsgroup && \
    useradd -u 10001 -g imsgroup -s /bin/bash -m imsuser && \
    mkdir -p /app/data /app/static /app/templates && \
    chown -R imsuser:imsgroup /app

# Copy application code
COPY --chown=imsuser:imsgroup src /app/src
COPY --chown=imsuser:imsgroup static /app/static
COPY --chown=imsuser:imsgroup templates /app/templates
COPY --chown=imsuser:imsgroup scripts /app/scripts
COPY --chown=imsuser:imsgroup pyproject.toml /app/pyproject.toml

# Switch to unprivileged runtime user
USER imsuser

# Volume mount point for persistent SQLite database and WAL logs
VOLUME ["/app/data"]

EXPOSE 8000

# Healthcheck probing /api/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Production WSGI/ASGI invocation with Uvicorn
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
