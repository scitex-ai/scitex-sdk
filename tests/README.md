# SDK test environments

The full SDK suite needs the declared contributor dependencies, including
Hatchling and the OpenAPI validator. From this checkout, install with:

```bash
python -m pip install --upgrade pip
python -m pip install -e '.[gui,chat,mcp,cli]' --group dev
python -m pytest tests/ -q -ra
SCITEX_ACCESS_STRICT=1 python -m pytest \
  tests/scitex_sdk/app/test_access_django.py \
  tests/scitex_sdk/app/api_access/test___init__.py -q -ra
```

The full suite configures no database so DB-free chat contracts remain valid.
The separate strict run configures real in-memory SQLite and rejects every
skip. Its two modules declare `django_db(transaction=True)` in strict mode:
pytest-django then permits the schema editor when that optional plugin is
installed. Without the plugin, the registered marker is inert and the same
SQLite proof runs. No plugin is disabled and the strict skip guard stays active.

The marker declarations live beside `_ACCESS_STRICT_PROOF` in those modules;
`tests/conftest.py` owns the SQLite configuration and
`tests/scitex_sdk/app/conftest.py` owns skip refusal. An installed runtime-only
`[all]` profile is not a substitute for the contributor environment. Record
source versus wheel imports, installed plugins, skipped scope and actual
results separately; these checks do not establish whole-Hub/browser acceptance.
