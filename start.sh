#!/bin/bash
# AVA — One-click startup script
# Run from the project root: bash start.sh

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Starting Docker (backend + postgres + qdrant) ==="
cd "$ROOT_DIR/infra"
docker-compose up --build -d

echo "=== Waiting for backend to be ready ==="
until curl -sf http://localhost:8000/health > /dev/null 2>&1; do
  sleep 2
  echo "  waiting..."
done
echo "  Backend is up!"

echo "=== Running Alembic migrations ==="
docker exec infra-backend-1 alembic upgrade head

echo "=== Installing frontend dependencies ==="
cd "$ROOT_DIR/frontend"
npm install --silent

echo "=== Starting frontend ==="
echo "  Opening http://localhost:3000"
npm run dev