# Multi-stage build for the FastAPI backend.
#
# Mainland-China builds: Docker Hub, PyPI and Debian apt are slow or blocked there.
# Override at build time (infra/docker-compose.prod.yml forwards these from infra/.env):
#   --build-arg PYTHON_IMAGE=<mirror-host>/python:3.12-slim
#   --build-arg UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple/
#   --build-arg APT_MIRROR=mirrors.aliyun.com
ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE} AS base
ENV PYTHONUNBUFFERED=1
# ffmpeg for video duration/processing; libs for Pillow are in slim already.
ARG APT_MIRROR=
RUN if [ -n "$APT_MIRROR" ]; then \
      sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
    fi \
    && apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
WORKDIR /app

# uv resolves project dependencies from this index (default PyPI; Aliyun mirror in China).
ARG UV_DEFAULT_INDEX=https://pypi.org/simple/
ENV UV_DEFAULT_INDEX=${UV_DEFAULT_INDEX}

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
