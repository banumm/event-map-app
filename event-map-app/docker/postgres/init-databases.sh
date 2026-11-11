#!/bin/sh
# Выполняется образом postgres один раз — при инициализации пустого тома.
# Database-per-service: events_db создаётся через POSTGRES_DB, здесь — users_db.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
	CREATE DATABASE ${USERS_DB_NAME:-users_db};
SQL
