DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'converter_api') THEN
        CREATE USER converter_api WITH PASSWORD '${API_USER_PASSWORD}';
    END IF;

    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'converter_consumer') THEN
        CREATE USER converter_consumer WITH PASSWORD '${CONSUMER_USER_PASSWORD}';
    END IF;
END
$$;

SELECT 'CREATE DATABASE crypto_converter OWNER converter_consumer'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'crypto_converter')\gexec

DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_database WHERE datname = 'crypto_converter') THEN
        EXECUTE 'GRANT CONNECT ON DATABASE crypto_converter TO converter_api';
        EXECUTE 'GRANT CONNECT ON DATABASE crypto_converter TO converter_consumer';
    END IF;
END
$$;