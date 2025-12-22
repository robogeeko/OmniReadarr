FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv pip install --system -r pyproject.toml

COPY . .

RUN mkdir -p /app/staticfiles

EXPOSE 8000

CMD ["gunicorn", "omnireadarr.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
