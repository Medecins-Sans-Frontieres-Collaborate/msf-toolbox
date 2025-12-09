"""Authentication helpers for Azure SDK clients.

Public API:
- get_credential() → TokenCredential
- AuthConfig (settings)
- Strategy (enum of auth strategies)
- GRAPH_DEFAULT_SCOPE (constant for Microsoft Graph)
- spo_scope_from_url(), authority_from_url() (scope helpers)
"""

from .config import AuthConfig
from .factory import get_credential
from .scopes import GRAPH_DEFAULT_SCOPE, authority_from_url, spo_scope_from_url

__all__ = [
    "AuthConfig",
    "get_credential",
    "GRAPH_DEFAULT_SCOPE",
    "spo_scope_from_url",
    "authority_from_url",
]
