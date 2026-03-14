# syntax=docker/dockerfile:1
# Multi-stage Dockerfile for production deployment with gunicorn

# -----------------------------------------------------------------------------
# Stage 1: Builder — install dependencies and collect static files
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build deps for psycopg and pillow (optional, reduces runtime image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtualenv and install dependencies (no dev groups)
ENV VIRTUAL_ENV=/app/.venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY pyproject.toml ./
# Install project and production dependencies only
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Copy application code
COPY . .

# collectstatic with inline env only (no ENV for secret-like values)
RUN DJANGO_SECRET_KEY=build-time-unused \
    DJANGO_DEBUG=False \
    DJANGO_ALLOWED_HOSTS=* \
    DATABASE_URL=sqlite:///tmp/db.sqlite3 \
    python manage.py collectstatic --noinput --clear

# -----------------------------------------------------------------------------
# Stage 2: Runtime — minimal image to run gunicorn
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime deps only (libpq for psycopg, no build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# Copy application, venv, and collected static files from builder
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"

# Own files and make entrypoint executable
RUN chown -R app:app /app \
    && chmod +x /app/docker/entrypoint.sh

USER app

# Run migrations then start the main process (e.g. gunicorn)
# Override CMD to change port/workers (e.g. --bind 0.0.0.0:9000)
EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", \
    "--bind", "0.0.0.0:8000", \
    "--workers", "4", \
    "--threads", "2", \
    "--worker-tmp-dir", "/dev/shm", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "--capture-output"]
