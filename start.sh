#!/bin/bash
# ============================================
# Startup script for Landa Beauty Supply API
# ============================================

echo "[START] Running database migrations..."
python -m alembic upgrade head && echo "[OK] Migrations completed" || echo "[WARN] Migrations failed - continuing anyway"

echo "[START] Starting Landa Beauty Supply API..."
exec python main.py
