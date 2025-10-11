#!/usr/bin/env bash
# Initialize the rss_reader PostgreSQL database and schema

set -euo pipefail

# --- CONFIGURATION ---
DB_NAME="rssdb"
DB_USER="postgres"
DB_PASSWORD="postgres"
DB_HOST="localhost"
DB_PORT="5432"
SCHEMA_FILE="app/models.sql"

echo "🔧 Initializing PostgreSQL database for rss_reader..."

# Check for psql
if ! command -v psql >/dev/null 2>&1; then
  echo "❌ Error: psql not found. Please install PostgreSQL client tools."
  exit 1
fi

# Export password so psql doesn't prompt
export PGPASSWORD="${DB_PASSWORD}"

# --- CREATE ROLE (if missing) ---
echo "👤 Ensuring database role '$DB_USER' exists..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "SELECT 1;" >/dev/null 2>&1 || {
  echo "Creating user '$DB_USER'..."
  psql -h "$DB_HOST" -p "$DB_PORT" -U "${USER}" -d postgres -c "CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}';"
}

# --- CREATE DATABASE ---
echo "🗄️  Creating database '$DB_NAME' (if not exists)..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}';" | grep -q 1 || \
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

# --- APPLY SCHEMA ---
if [[ -f "$SCHEMA_FILE" ]]; then
  echo "📄 Applying schema from $SCHEMA_FILE..."
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SCHEMA_FILE"
else
  echo "❌ Schema file not found at $SCHEMA_FILE"
  exit 1
fi

echo "✅ Database '$DB_NAME' initialized successfully!"

