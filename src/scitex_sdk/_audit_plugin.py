"""SDK-owned project auditor, federated through scitex-dev's public SPI."""


def check_header_contract(repo_root, violation_class, violations):
    """Report header ownership failures at mandatory error severity."""
    from .ui._linter._header_contract import scan_headers

    for finding in scan_headers(repo_root):
        violations.append(
            violation_class(
                "PS-SDK-HEADER", f"{finding.path}:{finding.line}", finding.detail
            )
        )


def check_filter_contract(repo_root, violation_class, violations):
    """Report filter chrome ownership at mandatory error severity."""
    from .ui._linter._filter_contract import scan_filters

    for finding in scan_filters(repo_root):
        violations.append(
            violation_class(
                "PS-SDK-FILTER", f"{finding.path}:{finding.line}", finding.detail
            )
        )


def get_plugin():
    """Load the scanner eagerly: an incomplete installation must not pass."""
    from .ui._linter._filter_contract import scan_filters
    from .ui._linter._header_contract import scan_headers

    if not callable(scan_headers) or not callable(scan_filters):
        raise TypeError("SDK chrome scanner is unavailable")
    return {
        "rules": [
            (
                "PS-SDK-HEADER",
                "UI",
                "SDK app-header and dropdown ownership",
                "E",
                "sdk-header-contract",
            ),
            (
                "PS-SDK-FILTER",
                "UI",
                "SDK filter chrome ownership",
                "E",
                "sdk-filter-contract",
            ),
        ],
        "checks": [check_header_contract, check_filter_contract],
    }
