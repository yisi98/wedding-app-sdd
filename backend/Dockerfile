# Multi-stage build for the FastAPI backend.
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1
# ffmpeg for video duration/processing; libs for Pillow are in slim already.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
