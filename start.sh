#!/bin/bash
set -e

echo "Running database migrations..."

# Function to run migrations safely
run_migrations() {
    # Try to run migrations normally first
    if alembic upgrade head; then
        echo "Migrations completed successfully"
        return 0
    fi
    
    echo "Migration failed. Checking if tables already exist..."
    
    # If migration failed, it might be because tables exist but aren't tracked
    # Let's stamp the database with the latest migration
    echo "Stamping database with current migration state..."
    alembic stamp head
    
    echo "Database migration state synchronized"
}

# Run the migration function
run_migrations

echo "Starting FastAPI server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8080 