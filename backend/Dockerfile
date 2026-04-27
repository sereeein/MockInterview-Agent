# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Install uv (fast Python package manager)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/

WORKDIR /app

# uv sync needs both pyproject.toml/uv.lock AND src/ available because hatchling
# verifies the package layout (src/mockinterview/) during sync. Copy all first,
# then sync. Trade-off: any source change invalidates the deps cache; acceptable
# for low-frequency deploys.
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:${PATH}"
# DB lives on a Railway-mounted Volume at /data (set DB_URL env to point here)
ENV DB_URL="sqlite:////data/app.db"
# Ensure /data exists even if volume isn't mounted (e.g. local docker run)
RUN mkdir -p /data

# Railway sets $PORT dynamically. Default to 8000 for local docker run.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn mockinterview.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
