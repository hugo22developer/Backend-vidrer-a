FROM ghcr.io/astral-sh/uv:0.5.11-python3.12-bookworm-slim

WORKDIR /app

# Dependencias del sistema para WeasyPrint (render de PDF en Docker)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libffi8 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    fonts-dejavu-core \
    fonts-inter \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock* ./
RUN if [ -f uv.lock ]; then uv sync --no-dev; else uv sync --no-dev; fi
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]

