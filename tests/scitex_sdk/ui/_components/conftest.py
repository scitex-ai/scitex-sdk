#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/tests/scitex_sdk/ui/_components/conftest.py

"""Per-component metadata tests — conftest.

The ``check_metadata`` fixture this directory's tests request is defined in
``tests/conftest.py`` (the root), not here. Measured 2026-09-17: defined here it
worked for directory-style runs and vanished under the CI shard runner's explicit
multi-file argument list, which is how every PR in this repo runs. The root
conftest is loaded whatever shape the arguments take.

The check itself lives in ``tests/_component_metadata.py`` so both files reference
one implementation without importing each other — a conftest is not a library,
however importable it looks.

# EOF
"""
