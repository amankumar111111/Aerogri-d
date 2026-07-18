# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

# Stage 2: Python dependencies (cached layer)
FROM python:3.12-slim AS deps
WORKDIR /app
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# Stage 3: Production image
FROM python:3.12-slim AS production

# Non-root user
RUN groupadd -r aerogrid && useradd -r -g aerogrid -d /app -s /sbin/nologin aerogrid

WORKDIR /app

# Copy installed dependencies
COPY --from=deps /install /usr/local

# Copy application code
COPY backend/app/ ./app/

# Copy frontend build
COPY --from=frontend-build /app/dist ./static/

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/v1/health')" || exit 1

# Switch to non-root user
USER aerogrid

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2", "--access-log"]
