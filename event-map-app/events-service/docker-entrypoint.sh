#!/bin/sh
# Применение миграций при старте контейнера (ПР7).
# БД может ещё подниматься — несколько попыток с паузой, затем выход с ошибкой.
set -e

attempts="${MIGRATION_ATTEMPTS:-10}"
i=1
until alembic upgrade head; do
  if [ "$i" -ge "$attempts" ]; then
    echo '{"level":"ERROR","service":"events-service","event":"migrations.failed"}'
    exit 1
  fi
  echo "{\"level\":\"WARNING\",\"service\":\"events-service\",\"event\":\"migrations.retry\",\"attempt\":$i}"
  i=$((i + 1))
  sleep 2
done
echo '{"level":"INFO","service":"events-service","event":"migrations.applied"}'

exec "$@"
