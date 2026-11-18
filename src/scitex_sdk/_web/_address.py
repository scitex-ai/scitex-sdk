"""Shared address formatting for GUI URLs and Django's bind parser."""


def _url_host(host: str) -> str:
    """Bracket an IPv6 literal, preserving already bracketed addresses."""
    return f"[{host}]" if ":" in host and not host.startswith("[") else host


def _server_address(host: str, port: int) -> str:
    """Return hostname:port or [IPv6]:port without changing the bind host."""
    return f"{_url_host(host)}:{port}"
