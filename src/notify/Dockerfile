FROM python:3.13-slim as builder

WORKDIR /app

RUN pip install --no-cache-dir uv>=0.1.0 && \
    uv venv /app/.venv

COPY pyproject.toml uv.lock ./

RUN . /app/.venv/bin/activate && \
    uv sync --group notify --group prod --frozen

FROM python:3.13-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY src/core ./core
COPY src/notify ./notify
COPY alembic.ini ./alembic.ini
COPY migrations/versions/notify ./migrations/versions/notify
COPY migrations/env.py migrations/utils.py ./migrations/

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv" \
    DB_NAME=notify

RUN chmod +x ./notify/run.sh

CMD ["/bin/bash", "-c", "/notify/run.sh"]
