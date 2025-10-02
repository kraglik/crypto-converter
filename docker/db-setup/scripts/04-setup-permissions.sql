\c crypto_converter

GRANT SELECT ON ALL TABLES IN SCHEMA public TO converter_api;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO converter_api;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO converter_consumer;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO converter_consumer;

GRANT SELECT, UPDATE ON part_config TO converter_consumer;
GRANT SELECT ON part_config_sub TO converter_consumer;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO converter_consumer;
GRANT EXECUTE ON ALL PROCEDURES IN SCHEMA public TO converter_consumer;