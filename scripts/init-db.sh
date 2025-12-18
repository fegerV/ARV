#!/bin/bash
set -e

# Create default database and user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'vertex_ar') THEN
            CREATE USER vertex_ar WITH PASSWORD 'password';
        END IF;
    END
    \$\$;
    
    SELECT 'CREATE DATABASE vertex_ar OWNER vertex_ar' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'vertex_ar');;
    GRANT ALL PRIVILEGES ON DATABASE vertex_ar TO vertex_ar;
EOSQL