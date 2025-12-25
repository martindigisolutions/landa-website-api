#!/bin/bash
# ============================================
# Startup script for Landa Beauty Supply API
# Runs migrations and then starts the app
# ============================================

set -e

echo "[START] Running database migrations..."
python -m alembic upgrade head || echo "[WARN] Migrations failed or already up to date"

echo "[START] Starting application..."
exec python main.py
