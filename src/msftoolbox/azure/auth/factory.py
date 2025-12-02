from __future__ import annotations

from azure.core.credentials import TokenCredential
from azure.identity import (
    AzureCliCredential,
    CertificateCredential,
    ClientSecretCredential,
    DefaultAzureCredential,
    InteractiveBrowserCredential,
    ManagedIdentityCredential,
    UsernamePasswordCredential,
)

from .config import AuthConfig, Strategy


def get_credential(config: AuthConfig | None = None) -> TokenCredential:
    """Construct a :class:`TokenCredential` based on :class:`AuthConfig`.

    Args:
        config: Auth configuration. If ``None``, default credential is used.

    Returns:
        A concrete :class:`TokenCredential`.
    """
    cfg = config or AuthConfig()
    authority = cfg.authority  # may be None

    match cfg.strategy:
        case Strategy.CLI:
            return AzureCliCredential(authority=authority)
        case Strategy.MANAGED_IDENTITY:
            return ManagedIdentityCredential(
                client_id=cfg.client_id, authority=authority
            )
        case Strategy.CLIENT_SECRET:
            return ClientSecretCredential(
                tenant_id=cfg.tenant_id,
                client_id=cfg.client_id,
                client_secret=cfg.client_secret.get_secret_value(),
                authority=authority,
            )
        case Strategy.CLIENT_CERTIFICATE:
            return CertificateCredential(
                tenant_id=cfg.tenant_id,
                client_id=cfg.client_id,
                certificate_path=str(cfg.certificate_path),
                password=(
                    cfg.certificate_password.get_secret_value()
                    if cfg.certificate_password
                    else None
                ),
                authority=authority,
            )
        # case Strategy.WORKLOAD_IDENTITY:
        #     return WorkloadIdentityCredential(
        #         tenant_id=cfg.tenant_id,
        #         client_id=cfg.client_id,
        #         token_file_path=str(cfg.federated_token_file),
        #         authority=authority,
        #     )
        case Strategy.INTERACTIVE_BROWSER:
            return InteractiveBrowserCredential(
                tenant_id=cfg.tenant_id,
                client_id=cfg.client_id,
                authority=authority,
                redirect_uri=cfg.redirect_uri,
            )
        case Strategy.USERNAME_PASSWORD:
            # client_id is recommended; tenant_id optional depending on app
            return UsernamePasswordCredential(
                tenant_id=cfg.tenant_id,
                client_id=cfg.client_id,
                username=cfg.username,
                password=(cfg.password.get_secret_value() if cfg.password else None),
                authority=authority,
                client_credentials=(
                    cfg.client_secret.get_secret_value() if cfg.client_secret else None
                ),
            )
        case _:
            return DefaultAzureCredential(authority=authority)
