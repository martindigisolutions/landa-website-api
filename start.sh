#!/bin/bash
# ============================================
# Startup script for Landa Beauty Supply API
# ============================================

echo "[START] Creating initial database tables (if needed)..."
python -c "from database import engine, Base; from models import *; Base.metadata.create_all(bind=engine)" && echo "[OK] Initial tables created/verified" || echo "[WARN] Could not create initial tables - continuing anyway"

echo "[START] Running database migrations..."
python -m alembic upgrade head && echo "[OK] Migrations completed" || echo "[WARN] Migrations failed - continuing anyway"

echo "[START] Starting Landa Beauty Supply API..."
exec python main.py

