\c crypto_converter

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename = 'quotes'
    ) THEN
        CREATE TABLE public.quotes (
            symbol            VARCHAR(40) NOT NULL,
            base_currency     VARCHAR(20) NOT NULL,
            quote_currency    VARCHAR(20) NOT NULL,
            rate              NUMERIC(36, 18) NOT NULL,
            quote_timestamp   TIMESTAMPTZ NOT NULL,
            created_at        TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (symbol, quote_timestamp)
        ) PARTITION BY RANGE (quote_timestamp);

        ALTER TABLE public.quotes OWNER TO converter_consumer;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_quotes_symbol_timestamp
    ON public.quotes (symbol, quote_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_quotes_timestamp
    ON public.quotes (quote_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_quotes_base_quote_timestamp
    ON public.quotes (base_currency, quote_currency, quote_timestamp DESC);

DO $$
DECLARE
    v_success boolean := false;
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_partman') THEN
        IF NOT EXISTS (
            SELECT 1 FROM part_config
            WHERE parent_table = 'public.quotes'
        ) THEN
            PERFORM create_parent(
                p_parent_table => 'public.quotes',
                p_control => 'quote_timestamp',
                p_type => 'range',
                p_interval => '1 day',
                p_premake => 7
            );

            UPDATE part_config
            SET retention = '7 days',
                retention_keep_table = false,
                retention_keep_index = false,
                infinite_time_partitions = true,
                inherit_privileges = true
            WHERE parent_table = 'public.quotes';

            PERFORM run_maintenance('public.quotes', p_jobmon := false);

            RAISE NOTICE 'pg_partman configured successfully for public.quotes';
            v_success := true;
        ELSE
            PERFORM run_maintenance('public.quotes', p_jobmon := false);
            RAISE NOTICE 'pg_partman already configured, maintenance run for public.quotes';
            v_success := true;
        END IF;
    ELSE
        RAISE WARNING 'pg_partman extension not installed';
    END IF;
END
$$;

-- Check that partman actually did its thing correctly
DO $$
DECLARE
    partition_count int;
BEGIN
    SELECT COUNT(*) INTO partition_count
    FROM pg_tables
    WHERE schemaname = 'public'
    AND tablename LIKE 'quotes_%';

    RAISE NOTICE 'Found % partition tables', partition_count;

    FOR r IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename LIKE 'quotes_%'
        ORDER BY tablename
    LOOP
        RAISE NOTICE 'Partition: %', r.tablename;
    END LOOP;
END
$$;