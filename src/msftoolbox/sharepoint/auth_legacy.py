"""Legacy helpers for constructing AuthConfig from deprecated kwargs."""

from __future__ import annotations

from warnings import warn

from msftoolbox.azure.auth.config import AuthConfig, Strategy


def _auth_from_legacy_kwargs(
    *,
    username: str | None,
    password: str | None,
    client_id: str | None,
    client_secret: str | None,
    interactive_auth: bool | None,
    tenant_id: str | None,
    thumbprint: str | None,  # kept for compatibility; ignored
    certificate_path: str | None,
) -> AuthConfig:
    """Translate legacy kwargs to an AuthConfig, validating per strategy.

    Args:
        username (Optional[str]): The username for authentication.
        password (Optional[str]): The password for authentication.
        client_id (Optional[str]): The client ID for app or interactive authentication.
        client_secret (Optional[str]): The client secret for app.
        interactive_auth (Optional[bool]): Boolean to indicate whether to request user consent to log in.
        tenant_id (Optional[str]): The ID for the Azure Tenant.
        thumbprint (Optional[str]): The hexadecimal thumbprint from your certificate
        certificate_path (Optional[str]): The path to the selfsigned certificate
    """
    warn(
        "Passing credential kwargs directly to SharePointFileClient is "
        "deprecated; construct an AuthConfig config instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # 1) Interactive browser
    if interactive_auth and client_id and tenant_id:
        return AuthConfig(
            strategy=Strategy.INTERACTIVE_BROWSER,
            client_id=client_id,
            tenant_id=tenant_id,
        )

    # 2) Client secret (requires tenant)
    if client_id and client_secret and tenant_id:
        return AuthConfig(
            strategy=Strategy.CLIENT_SECRET,
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
        )

    # 3) Client certificate (requires tenant + path)
    if client_id and tenant_id and certificate_path:
        return AuthConfig(
            strategy=Strategy.CLIENT_CERTIFICATE,
            client_id=client_id,
            tenant_id=tenant_id,
            certificate_path=certificate_path,
        )

    # 4) Username/password — only supported when paired with app registration (deprecated)
    if username and password and client_id and client_secret and tenant_id:
        return AuthConfig(
            strategy=Strategy.USERNAME_PASSWORD,
            client_id=client_id,
            client_secret=client_secret,
            tenant_id=tenant_id,
            username=username,
            password=password,
        )

    # Non-MFA username/password without an app is no longer supported
    if username or password:
        raise ValueError(
            "Username/password without an app registration is no longer supported. "
            "Register an app and use Strategy.USERNAME_PASSWORD (deprecated) or "
            "prefer INTERACTIVE_BROWSER / CLIENT_SECRET / CLIENT_CERTIFICATE."
        )

    raise ValueError(
        "Could not determine authentication strategy from legacy parameters. "
        "Provide 'auth=AuthConfig(...)' or include tenant_id with client_id/client_secret, "
        "or client_id/tenant_id/certificate_path for certificate auth."
    )
