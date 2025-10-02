#!/bin/sh
set -e

echo "Waiting for postgres to go online"

until PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d postgres -c '\q' 2>/dev/null; do
  echo "Can't reach postgres, sleeping"
  sleep 2
done

export API_USER_PASSWORD="${API_USER_PASSWORD}"
export CONSUMER_USER_PASSWORD="${CONSUMER_USER_PASSWORD}"

echo "Postgres is online, running scripts"

for script in $(ls /scripts/*.sql | sort); do
  echo "Executing $script"

  envsubst < "$script" | PGPASSWORD="$POSTGRES_PASSWORD" psql \
    -h "$POSTGRES_HOST" \
    -U "$POSTGRES_USER" \
    -d postgres \
    -a

  echo "Done"
done

echo "db setup done"