FROM postgres:16-alpine

RUN apk add --no-cache postgresql-client gettext

WORKDIR /scripts

COPY scripts/*.sql ./
COPY entrypoint.sh ./

RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]