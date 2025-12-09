from typing import TYPE_CHECKING

from msgraph import GraphServiceClient

from msftoolbox.azure.auth import get_credential, scopes

if TYPE_CHECKING:
    from azure.core.credentials import TokenCredential

    from msftoolbox.azure.auth.config import AuthConfig


def build_graph_client(
    auth_config: "AuthConfig" = None,
) -> tuple["GraphServiceClient", "TokenCredential"]:
    """Build a Graph ServiceClient using Azure authentication."""
    cred: TokenCredential = get_credential(auth_config)

    return (GraphServiceClient(cred, [scopes.GRAPH_DEFAULT_SCOPE]), cred)
