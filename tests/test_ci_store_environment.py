"""Real child-process isolation controls; no ambient database connections."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

GUARD = Path(__file__).resolve().parents[1] / "scripts/ci-store-environment.py"


def test_child_startup_removes_hostile_selectors_before_imports():
    # Arrange
    environment = dict(os.environ, PGSERVICE="hostile-service", PGHOST="fleet.invalid",
                       PGHOSTADDR="192.0.2.1", PGOPTIONS="hostile-options",
                       PGPASSWORD="synthetic-test-value", SCITEX_STORE_DSN="postgresql://fleet.invalid/db",
                       SCITEX_STORE_SCOPE="hostile-scope", SCITEX_CARDS_DB="postgresql://fleet.invalid/cards")
    code = """
import os, json
from pathlib import Path
assert not {'PGSERVICE','PGHOSTADDR','PGOPTIONS','PGPASSWORD','SCITEX_STORE_SCOPE'} & os.environ.keys()
assert os.environ['SCITEX_STORE_DSN'].startswith('postgresql://sdk_test@/sdk_test?host=/tmp/sdk-no-store-')
assert os.environ['SCITEX_CARDS_DB'] == os.environ['SCITEX_STORE_DSN']
root = Path(os.environ['PGPASSFILE']).parent
assert root.stat().st_uid == os.getuid() and root.stat().st_mode & 0o777 == 0o700
assert not Path(os.environ['PGHOST']).exists()
assert Path(os.environ['PGPASSFILE']).read_bytes() == b''
assert Path(os.environ['PGSERVICEFILE']).read_bytes() == b''
print(json.dumps({'root':str(root)}))
"""
    # Act
    baseline = subprocess.run([sys.executable, "-I", "-c", code], env=environment,
                              capture_output=True, text=True, timeout=10)
    if baseline.returncode == 0:
        raise AssertionError("unwrapped inherited environment must fail the same safety control")
    child = subprocess.run([sys.executable, "-I", "-S", str(GUARD), "--",
                            sys.executable, "-I", "-c", code], env=environment,
                           capture_output=True, text=True, timeout=10)
    if child.returncode:
        raise AssertionError(child.stderr)
    root = Path(json.loads(child.stdout)["root"])
    shutil.rmtree(root)
    # Assert
    assert child.returncode == 0


def test_explicit_owned_sqlite_fixture_still_operates(tmp_path):
    # Arrange
    database = tmp_path / "fixture.sqlite3"
    code = """
import os, sqlite3, sys
from pathlib import Path
assert 'PGSERVICE' not in os.environ
with sqlite3.connect(sys.argv[1]) as connection:
    connection.execute('CREATE TABLE owned_fixture(value TEXT)')
    connection.execute("INSERT INTO owned_fixture VALUES ('fixture')")
    assert connection.execute('SELECT value FROM owned_fixture').fetchone() == ('fixture',)
print(Path(os.environ['PGPASSFILE']).parent)
"""
    # Act
    child = subprocess.run([sys.executable, "-I", "-S", str(GUARD), "--",
                            sys.executable, "-I", "-c", code, str(database)],
                           env=dict(os.environ, PGSERVICE="hostile-service"),
                           capture_output=True, text=True, timeout=10)
    if child.returncode:
        raise AssertionError(child.stderr)
    shutil.rmtree(Path(child.stdout.strip()))
    # Assert
    assert database.is_file()


def test_local_collection_floor_removes_rather_than_blanks_selectors():
    # Arrange
    spec = importlib.util.spec_from_file_location("sdk_store_floor_control", GUARD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    environment = {"PGSERVICE": "hostile", "SCITEX_STORE_DSN": "postgresql://fleet.invalid/db", "UNCHANGED": "value"}
    # Act
    root = module.protect_environment(environment)
    try:
        result = ("PGSERVICE" not in environment, environment["UNCHANGED"], (root / "pgpass").stat().st_mode & 0o777)
    finally:
        shutil.rmtree(root)
    # Assert
    assert result == (True, "value", 0o600)


def test_phase_preserves_child_failure_status():
    # Arrange
    # Act
    child = subprocess.run([sys.executable, "-I", "-S", str(GUARD), "--",
                            sys.executable, "-I", "-c", "raise SystemExit(23)"],
                           capture_output=True, timeout=10)
    # Assert
    assert child.returncode == 23


def test_real_dev_store_resolves_floor_and_explicit_fixture_without_network():
    # Arrange
    code = """
import os, sys
from pathlib import Path
def no_network(event, args):
    if event == 'socket.connect':
        raise AssertionError('store resolution must not connect')
sys.addaudithook(no_network)
from scitex_dev.store import host_store
assert host_store(pkg='sdk-floor-control').dsn == os.environ['SCITEX_STORE_DSN']
assert 'PGSERVICE' not in os.environ
root = Path(os.environ['PGPASSFILE']).parent
os.environ['SCITEX_STORE_DSN'] = 'postgresql://owned_fixture@/fixture?host=' + str(root / 'fixture')
assert host_store(pkg='sdk-fixture-control').dsn == os.environ['SCITEX_STORE_DSN']
print(root)
"""
    # Act
    child = subprocess.run([sys.executable, "-I", "-S", str(GUARD), "--",
                            sys.executable, "-I", "-c", code],
                           env=dict(os.environ, PGSERVICE="hostile-service"),
                           capture_output=True, text=True, timeout=10)
    if child.returncode:
        raise AssertionError(child.stderr)
    shutil.rmtree(Path(child.stdout.strip()))
    # Assert
    assert child.returncode == 0


def test_actual_bash_phase_cannot_reintroduce_service_from_inherited_startup(tmp_path):
    # Arrange
    startup = tmp_path / "owned-startup-fixture.sh"
    startup.write_text("export PGSERVICE=synthetic-reintroduced\n")
    environment = dict(os.environ, BASH_ENV=str(startup), ENV=str(startup))
    phase = 'test -z "${PGSERVICE+x}"; test -z "${BASH_ENV+x}"; printf "%s\\n" "$PGSYSCONFDIR"'
    # Act
    baseline = subprocess.run(["bash", "-euo", "pipefail", "-c", phase],
                              env=environment, capture_output=True, timeout=5)
    if baseline.returncode == 0:
        raise AssertionError("the real unguarded shell must exhibit the startup-file bypass")
    child = subprocess.run([sys.executable, "-I", "-S", str(GUARD), "--",
                            "bash", "-euo", "pipefail", "-c", phase],
                           env=environment, capture_output=True, text=True, timeout=5)
    if child.returncode:
        raise AssertionError(child.stderr)
    shutil.rmtree(Path(child.stdout.strip()))
    # Assert
    assert child.returncode == 0
