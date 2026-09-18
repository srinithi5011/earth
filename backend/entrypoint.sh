#!/usr/bin/env sh
set -e

echo "[entrypoint] Waiting for database..."
python - <<'PYEOF'
import time
import sys
sys.path.insert(0, ".")
from sqlalchemy import text
from app.models.database import engine

for attempt in range(30):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[entrypoint] Database is ready.")
        break
    except Exception as exc:  # noqa: BLE001
        print(f"[entrypoint] DB not ready yet ({exc}); retrying...")
        time.sleep(2)
else:
    print("[entrypoint] Database never became ready; continuing anyway.")
PYEOF

echo "[entrypoint] Initializing schema..."
python -c "from app.models.database import init_db; init_db()"

echo "[entrypoint] Seeding knowledge base (idempotent)..."
python /app/scripts_in_container/seed.py || echo "[entrypoint] Seed step skipped/failed non-fatally."

echo "[entrypoint] Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
