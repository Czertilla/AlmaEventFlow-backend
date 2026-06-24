#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname="$POSTGRES_DB" <<-EOSQL
   SELECT 'CREATE DATABASE "user"' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'user')\gexec
   SELECT 'CREATE DATABASE "mail"' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mail')\gexec
   SELECT 'CREATE DATABASE "profile"' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'profile')\gexec
   SELECT 'CREATE DATABASE "org"' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'org')\gexec
   SELECT 'CREATE DATABASE "event"' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'event')\gexec
   SELECT 'CREATE DATABASE "geo"' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'geo')\gexec
   SELECT 'CREATE DATABASE "notify"' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'notify')\gexec
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname="geo" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS postgis;
    CREATE EXTENSION IF NOT EXISTS postgis_topology;
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
EOSQL
