"""Run SDK non-database CI phases without inherited fleet-store routing.

Bootstrap with ``python3 -I -S`` before pip/build/test startup. No peer imports,
database connection, or persistence proof. Fixtures may explicitly override this
refusal target after startup; no PG service selector survives the floor.
"""
import os
import sys
import tempfile
from pathlib import Path


def protect_environment(environment):
    """Remove ambient selectors and create private, deliberately absent sockets."""
    root = Path(tempfile.mkdtemp(prefix="sdk-no-store-", dir="/tmp"))
    for key in tuple(environment):
        if key.startswith(("PG", "SCITEX_STORE_")) or key in {
            "SCITEX_CARDS_DB", "SCITEX_CLEW_PROJECT",
        }:
            del environment[key]
    for name in ("pgpass", "pgservice.conf"):
        path = root / name
        path.touch(mode=0o600, exist_ok=False)
    dsn = f"postgresql://sdk_test@/sdk_test?host={root / 'unavailable'}&connect_timeout=1"
    environment.update(
        SCITEX_STORE_DSN=dsn,
        SCITEX_CARDS_DB=dsn,
        SCITEX_CLEW_PROJECT="owned-sdk-" + root.name,
        PGHOST=str(root / "unavailable"), PGPORT="5432",
        PGUSER="sdk_test", PGDATABASE="sdk_test", PGCONNECT_TIMEOUT="1",
        PGPASSFILE=str(root / "pgpass"),
        PGSERVICEFILE=str(root / "pgservice.conf"), PGSYSCONFDIR=str(root),
    )
    return root


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "--":
        raise SystemExit("usage: python3 -I -S ci-store-environment.py -- COMMAND [ARG ...]")
    child_environment = os.environ.copy()
    protect_environment(child_environment)
    # exec preserves phase signal/exit behavior, including fail-loud test gates.
    os.execvpe(sys.argv[2], sys.argv[2:], child_environment)
