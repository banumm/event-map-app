#!/bin/sh
# Применение миграций Django и создание администратора при старте (ПР7).
set -e

attempts="${MIGRATION_ATTEMPTS:-10}"
i=1
until python manage.py migrate --noinput; do
  if [ "$i" -ge "$attempts" ]; then
    echo '{"level":"ERROR","service":"users-service","event":"migrations.failed"}'
    exit 1
  fi
  echo "{\"level\":\"WARNING\",\"service\":\"users-service\",\"event\":\"migrations.retry\",\"attempt\":$i}"
  i=$((i + 1))
  sleep 2
done
echo '{"level":"INFO","service":"users-service","event":"migrations.applied"}'

# Администратор создаётся, только если заданы переменные; повторный запуск
# не считается ошибкой (пользователь уже есть).
if [ -n "$DJANGO_ADMIN_USERNAME" ] && [ -n "$DJANGO_ADMIN_PASSWORD" ]; then
  python manage.py create_admin \
    --username "$DJANGO_ADMIN_USERNAME" \
    --email "${DJANGO_ADMIN_EMAIL:-admin@example.com}" \
    --password "$DJANGO_ADMIN_PASSWORD" \
    || echo '{"level":"INFO","service":"users-service","event":"admin.exists"}'
fi

exec "$@"
