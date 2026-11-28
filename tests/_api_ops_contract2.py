"""A leaf declaration that claims a contract major this SDK does not serve.

``build_plugin`` refuses contract "2", so the declaration is the shipped notes
plugin with its stored major replaced: exactly what a host reads back from the
inert descriptor of a leaf built against a newer SDK.
"""

import dataclasses

from tests._api_ops_leaf import PLUGIN as _NOTES

PLUGIN = dataclasses.replace(_NOTES, contract="2")
