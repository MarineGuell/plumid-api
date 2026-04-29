#!/bin/sh
# PlumID API entrypoint
# ------------------------------------------------------------------
# 1. Wait until the database accepts connections
# 2. Exec the requested command (uvicorn, celery, a shell, …)
#
# Note: schema + roles + seed data are built once by the postgres
# container's init script (db/initdb/01-schema.sql), so we do NOT
# run `alembic upgrade head` here. The application role plumid_app
# has no CREATE privilege on `public` and would fail anyway.
set -e

echo "⟡ PlumID API starting…"

if [ -n "$PORT" ]; then
    echo "⟡ Binding to PORT=$PORT"
fi

# Wait for the database to be reachable. Uses the same DSN as the app
# so it also validates credentials & permissions, not just TCP.
echo "⟡ Waiting for database…"
python - <<'PYEOF'
import sys, time
sys.path.insert(0, "/app")
from sqlalchemy import create_engine, text
from settings import settings

deadline = time.time() + 60
last = None
while time.time() < deadline:
    try:
        with create_engine(settings.db_url, pool_pre_ping=True).connect() as cx:
            cx.execute(text("SELECT 1"))
        print("⟡ Database OK")
        sys.exit(0)
    except Exception as e:
        last = e
        time.sleep(1)
print(f"⟡ Database unreachable: {last}", file=sys.stderr)
sys.exit(1)
PYEOF

echo "⟡ Handing off to: $*"
exec "$@"