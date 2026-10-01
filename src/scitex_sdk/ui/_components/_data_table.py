#!/usr/bin/env python3
"""DataTable component metadata."""

from .._registry import register_component


class DataTable:
    name = "data-table"
    version = "0.1.0"
    description = (
        "Full spreadsheet component with selection, editing, virtual scroll, CSV import"
    )
    ts_entry = "scitex_sdk/ui/ts/app/data-table/index"
    css_file = "scitex_sdk/ui/css/app/data-table.css"


register_component(DataTable.name, DataTable)
