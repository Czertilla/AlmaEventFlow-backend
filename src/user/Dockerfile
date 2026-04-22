# ===== BUILD STAGE =====
FROM python:3.13-slim as builder

WORKDIR /app

# 1. Установка uv и создание виртуального окружения
RUN pip install --no-cache-dir uv>=0.1.0 && \
    uv venv /app/.venv

# 2. Копирование файлов зависимостей
COPY pyproject.toml uv.lock ./

# 3. Установка зависимостей через uv в виртуальное окружение
RUN . /app/.venv/bin/activate && \
    uv sync --group user --group prod --frozen

# ===== RUNTIME STAGE =====
FROM python:3.13-slim

WORKDIR /app

# 1. Перенос виртуальное окружение и код
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY src/core ./core
COPY src/user ./user
# 1.1 Перенос миграций
COPY alembic.ini ./alembic.ini
COPY migrations/versions/user ./migrations/versions/user
COPY migrations/env.py migrations/utils.py ./migrations/

# 2. Настройка окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv" \
    DB_NAME=user

# 3. Установка прав и проверка
RUN chmod +x ./user/run.sh


# 4. Точка входа
CMD ["/bin/bash", "-c", "/user/run.sh"]