from typing import Final
from urllib.parse import urlparse

GRAPH_DEFAULT_SCOPE: Final[str] = "https://graph.microsoft.com/.default"


def authority_from_url(site_url: str) -> str:
    """Return the URL authority (scheme + host).

    Args:
        site_url: Absolute SharePoint site URL (e.g., "https://tenant.sharepoint.com/sites/foo").

    Returns:
        The "<scheme>://<host>" portion of the URL.

    Raises:
        ValueError: If ``site_url`` is not absolute or lacks a host.
    """
    parsed = urlparse(site_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("site_url must be an absolute URL")
    return f"{parsed.scheme}://{parsed.netloc}"


def spo_scope_from_url(site_url: str) -> str:
    return f"{authority_from_url(site_url)}/.default"
