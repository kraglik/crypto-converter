\c crypto_converter

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        DELETE FROM cron.job WHERE jobname IN ('partman-maintenance', 'partman-retention');

        PERFORM cron.schedule(
            'partman-maintenance',
            '0 * * * *',
            'SELECT run_maintenance(p_jobmon := false);'
        );

        PERFORM cron.schedule(
            'partman-retention',
            '0 2 * * *',
            'SELECT run_maintenance(p_jobmon := false, p_analyze := false);'
        );

        RAISE NOTICE 'Cron jobs scheduled for partman maintenance';
    ELSE
        RAISE WARNING 'pg_cron not found, manual partition management required';
    END IF;
END
$$;