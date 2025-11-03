from time import time
from typing import TYPE_CHECKING

from office365.runtime.auth.token_response import TokenResponse
from office365.sharepoint.client_context import ClientContext

from msftoolbox.azure.auth import get_credential, scopes

if TYPE_CHECKING:
    from msftoolbox.azure.auth.config import AuthConfig


def build_client_context(
    site_url: str, auth_config: "AuthConfig" = None
) -> ClientContext:
    cred = get_credential(auth_config)
    scope = scopes.spo_scope_from_url(site_url)

    def _factory() -> TokenResponse:
        tok = cred.get_token(scope)
        return TokenResponse.from_json(
            {
                "token_type": "Bearer",
                "access_token": tok.token,
                "expires_in": max(1, int(tok.expires_on - time())),
            }
        )

    return ClientContext(site_url).with_access_token(_factory)
