\c crypto_converter

CREATE EXTENSION IF NOT EXISTS pg_partman SCHEMA public;

CREATE EXTENSION IF NOT EXISTS pg_cron;

GRANT USAGE ON SCHEMA public TO converter_api;
GRANT USAGE ON SCHEMA public TO converter_consumer;
GRANT USAGE ON SCHEMA cron TO converter_consumer;

GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO converter_consumer;
GRANT ALL ON ALL TABLES IN SCHEMA public TO converter_consumer;
