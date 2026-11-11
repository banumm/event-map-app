#!/usr/bin/env bash
# Сквозная проверка системы, поднятой через docker compose (ПР7, финальная проверка).
#
#   docker compose up -d --build --wait
#   bash scripts/smoke_test.sh            # обычная проверка
#   bash scripts/smoke_test.sh --db-down  # + остановка БД и проверка /health и кэша
#
# Повторяет ключевые сценарии ПР2–ПР6 внутри контейнеров: health, регистрация
# и вход (JWT), роли, CRUD событий, кэш (MISS/HIT/инвалидация), межсервисная
# проверка события в attendance-service, отказ БД.

set -euo pipefail

USERS=${USERS_URL:-http://localhost:8000}
EVENTS=${EVENTS_URL:-http://localhost:5001}
ATTEND=${ATTENDANCE_URL:-http://localhost:5002}
RUN_ID=$(date +%s)
PASS=0
FAIL=0

# Поле из тела последнего ответа: body_field id  /  body_field access_token
body_field() {
  python3 -c "import json,sys
try: print(json.load(open('/tmp/smoke_body'))[sys.argv[1]])
except Exception: print('')" "$1"
}

# request METHOD URL [BODY] [TOKEN] -> тело в /tmp/smoke_body, статус в $STATUS, заголовки в $HEADERS.
# Вызывать без $(...) и без конвейера: иначе STATUS останется в подоболочке.
request() {
  local method=$1 url=$2 body=${3:-} token=${4:-}
  local args=(-s -o /tmp/smoke_body -D /tmp/smoke_headers -w '%{http_code}' -X "$method" "$url"
              -H 'Content-Type: application/json' -H "X-Request-ID: smoke-$RUN_ID")
  [ -n "$body" ] && args+=(-d "$body")
  [ -n "$token" ] && args+=(-H "Authorization: Bearer $token")
  STATUS=$(curl "${args[@]}" || echo 000)
  HEADERS=$(cat /tmp/smoke_headers 2>/dev/null || true)
}

check() {  # check "описание" ожидаемый_статус [ожидаемый X-Cache]
  local name=$1 expected=$2 cache=${3:-}
  local got_cache
  got_cache=$(printf '%s' "$HEADERS" | tr -d '\r' | awk -F': ' 'tolower($1)=="x-cache"{print $2}')
  if [ "$STATUS" = "$expected" ] && { [ -z "$cache" ] || [ "$got_cache" = "$cache" ]; }; then
    PASS=$((PASS + 1)); printf '  [OK]   %-55s %s %s\n' "$name" "$STATUS" "$got_cache"
  else
    FAIL=$((FAIL + 1)); printf '  [FAIL] %-55s got %s %s, expected %s %s\n' "$name" "$STATUS" "$got_cache" "$expected" "$cache"
    head -c 300 /tmp/smoke_body; echo
  fi
}

echo "== 1. Health и метрики"
request GET "$USERS/health";   check "users-service /health" 200
request GET "$EVENTS/health";  check "events-service /health (БД доступна)" 200
request GET "$ATTEND/health";  check "attendance-service /health (events доступен)" 200
request GET "$EVENTS/metrics"; check "events-service /metrics" 200

echo "== 2. Аутентификация (ПР4)"
ORG="org$RUN_ID"; USR="usr$RUN_ID"
request POST "$USERS/auth/register" "{\"username\":\"$ORG\",\"email\":\"$ORG@example.com\",\"password\":\"StrongPass123\",\"role\":\"organizer\"}"
check "регистрация организатора" 201
request POST "$USERS/auth/register" "{\"username\":\"$ORG\",\"email\":\"$ORG@example.com\",\"password\":\"StrongPass123\",\"role\":\"organizer\"}"
check "повторная регистрация → 409" 409
request POST "$USERS/auth/register" "{\"username\":\"$USR\",\"email\":\"$USR@example.com\",\"password\":\"StrongPass123\",\"role\":\"user\"}"
check "регистрация пользователя" 201
request POST "$USERS/auth/login" "{\"username\":\"$ORG\",\"password\":\"StrongPass123\"}"
check "вход организатора (JWT)" 200
ORG_TOKEN=$(body_field access_token)
request POST "$USERS/auth/login" "{\"username\":\"$USR\",\"password\":\"StrongPass123\"}"
check "вход пользователя (JWT)" 200
USR_TOKEN=$(body_field access_token)
request POST "$USERS/auth/login" "{\"username\":\"$USR\",\"password\":\"wrong-pass\"}"
check "неверный пароль → 401" 401

echo "== 3. CRUD событий и роли (ПР2, ПР4)"
EVENT='{"title":"Концерт в парке","description":"Живая музыка","lat":43.2389,"lng":76.8897,"starts_at":"2026-12-20T19:00:00Z","category":"concert"}'
request POST "$EVENTS/events" "$EVENT";                 check "создание без токена → 401" 401
request POST "$EVENTS/events" "$EVENT" "$USR_TOKEN";    check "создание ролью user → 403" 403
request POST "$EVENTS/events" '{"title":"x"}' "$ORG_TOKEN"; check "невалидные данные → 400" 400
request POST "$EVENTS/events" "$EVENT" "$ORG_TOKEN"
check "создание организатором → 201" 201
EVENT_ID=$(body_field id)

echo "== 4. Кэш (ПР6)"
request GET "$EVENTS/events?limit=50";  check "GET /events — первый запрос" 200 MISS
request GET "$EVENTS/events?limit=50";  check "GET /events — повтор в пределах TTL" 200 HIT
request GET "$EVENTS/events/$EVENT_ID"; check "GET /events/{id} — первый запрос" 200 MISS
request GET "$EVENTS/events/$EVENT_ID"; check "GET /events/{id} — повтор" 200 HIT
request PATCH "$EVENTS/events/$EVENT_ID" '{"title":"Концерт перенесён"}' "$ORG_TOKEN"
check "PATCH события → 200" 200
request GET "$EVENTS/events/$EVENT_ID"
check "после PATCH кэш сброшен" 200 MISS
TITLE=$(body_field title)
[ "$TITLE" = "Концерт перенесён" ] && { PASS=$((PASS+1)); echo "  [OK]   в ответе новое название"; } \
  || { FAIL=$((FAIL+1)); echo "  [FAIL] в ответе старое название: $TITLE"; }
request GET "$EVENTS/events?limit=50";  check "список после PATCH" 200 MISS

echo "== 5. Attendance → events-service"
request POST "$ATTEND/attendance" "{\"event_id\":\"$EVENT_ID\",\"status\":\"going\"}" "$USR_TOKEN"
check "отметка на существующее событие → 201" 201
request POST "$ATTEND/attendance" '{"event_id":"00000000-0000-0000-0000-000000000000","status":"going"}' "$USR_TOKEN"
check "отметка на несуществующее событие → 404" 404
request GET "$ATTEND/attendance/event/$EVENT_ID"
check "счётчик участников" 200

if [ "${1:-}" = "--db-down" ]; then
  echo "== 6. Отказ базы данных"
  request GET "$EVENTS/events?limit=50"   # прогреваем кэш
  docker compose stop db >/dev/null 2>&1
  sleep 2
  request GET "$EVENTS/health";  check "events-service /health при остановленной БД → 503" 503
  request GET "$USERS/health";   check "users-service /health при остановленной БД → 503" 503
  request GET "$EVENTS/events?limit=50"; check "закэшированный список отдаётся без БД" 200 HIT
  request GET "$EVENTS/events?limit=7";  check "незакэшированный запрос → 503, без падения" 503
  docker compose start db >/dev/null 2>&1
  for _ in $(seq 1 30); do
    request GET "$EVENTS/health"; [ "$STATUS" = 200 ] && break; sleep 1
  done
  check "events-service /health после запуска БД → 200" 200
fi

echo "== 7. Удаление"
request DELETE "$EVENTS/events/$EVENT_ID" "" "$ORG_TOKEN"; check "DELETE → 204" 204
request GET "$EVENTS/events/$EVENT_ID";                    check "после удаления → 404" 404

echo
echo "Итог: пройдено $PASS, ошибок $FAIL"
[ "$FAIL" -eq 0 ]
