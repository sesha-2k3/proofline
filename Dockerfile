# Proofline: one image serving the SPA, /api, and /samples from FastAPI.

# --- Stage 1: build the frontend ---
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: backend runtime ---
FROM python:3.12-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PORT=8000
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock backend/.python-version backend/README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/app ./app
COPY backend/samples ./samples
COPY rules /app/rules
COPY --from=frontend /app/frontend/dist /app/frontend/dist
ENV PATH="/app/backend/.venv/bin:$PATH"
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
