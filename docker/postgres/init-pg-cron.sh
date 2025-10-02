#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    ALTER SYSTEM SET shared_preload_libraries = 'pg_cron,pg_partman_bgw';
    ALTER SYSTEM SET cron.database_name = 'crypto_converter';
    ALTER SYSTEM SET pg_partman_bgw.interval = 3600;
    ALTER SYSTEM SET pg_partman_bgw.role = 'postgres';
    ALTER SYSTEM SET pg_partman_bgw.dbname = 'crypto_converter';
EOSQL

echo "pg_cron configuration prepared"