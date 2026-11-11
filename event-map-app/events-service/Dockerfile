# events-service — образ приложения (ПР7)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=5001

WORKDIR /app

# Непривилегированный пользователь: приложение не работает от root.
RUN groupadd --system app && useradd --system --gid app --home-dir /app app

# Зависимости — отдельным слоем: при изменении кода он берётся из кэша.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=app:app . .
RUN chmod +x docker-entrypoint.sh

USER app
EXPOSE 5001

# Entrypoint применяет миграции Alembic, затем запускает команду CMD.
ENTRYPOINT ["./docker-entrypoint.sh"]
# gunicorn — production WSGI-сервер. Один воркер с потоками: кэш (ПР6)
# живёт в памяти процесса, и инвалидация должна видеть все записи.
CMD ["sh", "-c", "exec gunicorn app:app --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 30 --graceful-timeout 10"]
