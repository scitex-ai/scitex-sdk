#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: /home/ywatanabe/proj/scitex-ui/src/scitex_sdk/ui/__main__.py

"""Entry point for `python -m scitex_sdk.ui`.

Per scitex-dev audit-project PS105: every distribution must be runnable
via `python -m <package>`. Delegates to the Click CLI defined in
`scitex_sdk.ui._cli`.
"""

from scitex_sdk.ui._cli import main

if __name__ == "__main__":
    main()
