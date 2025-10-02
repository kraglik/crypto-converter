FROM postgres:16

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        postgresql-16-partman \
        postgresql-16-cron \
    && rm -rf /var/lib/apt/lists/*

COPY init-pg-cron.sh /docker-entrypoint-initdb.d/99-init-pg-cron.sh
RUN chmod +x /docker-entrypoint-initdb.d/99-init-pg-cron.sh