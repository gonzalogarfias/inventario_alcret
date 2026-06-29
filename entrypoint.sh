#!/bin/sh
set -e

host="${DB_HOST:-db}"
port="${DB_PORT:-5432}"
user="${DB_USER:-postgres}"
timeout=60
elapsed=0

echo "Waiting for PostgreSQL at $host:$port..."

until pg_isready -h "$host" -p "$port" -U "$user" -q 2>/dev/null || [ "$elapsed" -ge "$timeout" ]; do
  sleep 1
  elapsed=$((elapsed + 1))
done

if [ "$elapsed" -ge "$timeout" ]; then
  echo "ERROR: PostgreSQL did not become ready within ${timeout}s"
  exit 1
fi

echo "PostgreSQL is ready"

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
