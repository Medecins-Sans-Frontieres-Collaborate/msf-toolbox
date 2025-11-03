from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Strategy(str, Enum):
    """Supported authentication strategies."""

    DEFAULT = "default"
    CLI = "cli"
    MANAGED_IDENTITY = "managed_identity"
    CLIENT_SECRET = "client_secret"
    CLIENT_CERTIFICATE = "client_certificate"
    # WORKLOAD_IDENTITY = "workload_identity"  # TODO: Implement Workload Identity
    INTERACTIVE_BROWSER = "interactive_browser"
    USERNAME_PASSWORD = "username_password"  # Deprecated 30 September, 2025


class AuthConfig(BaseSettings):
    """Configuration for selecting and constructing Azure credentials.

    This model reads environment variables automatically using the ``AZURE_``
    prefix (e.g., ``AZURE_TENANT_ID``) and performs cross-field validation
    based on the selected :class:`Strategy`.

    Environment variables (aliases supported where noted):
        - AZURE_AUTH_STRATEGY
        - AZURE_TENANT_ID
        - AZURE_CLIENT_ID (alias: AZURE_MANAGED_IDENTITY_CLIENT_ID)
        - AZURE_CLIENT_SECRET
        - AZURE_CLIENT_CERTIFICATE_PATH
        - AZURE_CLIENT_CERTIFICATE_PASSWORD
        - AZURE_FEDERATED_TOKEN_FILE
        - AZURE_AUTHORITY_HOST
    """

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    # In Pydantic v2, when you set validation_alias="SOME_ENV_NAME" (or even an AliasChoices),
    # the field name itself is no longer used for input extraction unless you explicitly include
    # it in the alias choices. This is why I add the field name to alias choices.

    strategy: Strategy = Field(
        default=Strategy.DEFAULT,
        validation_alias=AliasChoices("strategy", "AUTH_STRATEGY", "STRATEGY"),
    )
    tenant_id: str | None = Field(
        default=None, validation_alias=AliasChoices("tenant_id", "TENANT_ID")
    )
    client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "client_id", "CLIENT_ID", "MANAGED_IDENTITY_CLIENT_ID"
        ),
    )
    client_secret: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("client_secret", "CLIENT_SECRET"),
    )
    certificate_path: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("certificate_path", "CLIENT_CERTIFICATE_PATH"),
    )
    certificate_password: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "certificate_password", "CLIENT_CERTIFICATE_PASSWORD"
        ),
    )
    federated_token_file: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("federated_token_file", "FEDERATED_TOKEN_FILE"),
    )
    username: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("username", "USERNAME"),
    )
    password: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("password", "PASSWORD"),
    )
    redirect_uri: str | None = Field(
        default="http://localhost:8400",
        validation_alias=AliasChoices("redirect_uri", "REDIRECT_URI"),
    )
    authority: str | None = Field(
        default=None,
        validation_alias=AliasChoices("authority", "AUTHORITY_HOST"),
    )

    @field_validator("certificate_path", "federated_token_file")
    @classmethod
    def _ensure_existing_path(cls, v: Path | None) -> Path | None:
        """Ensure configured paths exist if provided."""
        if v is not None and not v.exists():
            raise ValueError(f"Path does not exist: {v}")
        return v

    @model_validator(mode="after")
    def _cross_field_validation(self) -> "AuthConfig":
        """Validate required fields for the selected strategy."""
        s = self.strategy
        if s is Strategy.CLIENT_SECRET:
            if not (self.tenant_id and self.client_id and self.client_secret):
                raise ValueError(
                    "client_secret requires tenant_id, client_id, and client_secret."
                )
        elif s is Strategy.CLIENT_CERTIFICATE:
            if not (self.tenant_id and self.client_id and self.certificate_path):
                raise ValueError(
                    "client_certificate requires tenant_id, client_id, and certificate_path."
                )
        # elif s is Strategy.WORKLOAD_IDENTITY:
        #     if not (self.tenant_id and self.client_id and self.federated_token_file):
        #         raise ValueError(
        #             "workload_identity requires tenant_id, client_id, and federated_token_file."
        #         )
        elif s is Strategy.USERNAME_PASSWORD:
            if not (
                self.tenant_id
                and self.client_id
                and self.username
                and self.password
                and self.client_secret
            ):
                raise ValueError(
                    "username_password requires tenant_id, client_id, username, password and client_secret."
                )
        elif s is Strategy.INTERACTIVE_BROWSER:
            if not (self.tenant_id and self.client_id and self.redirect_uri):
                raise ValueError(
                    "interactive_broswer requires tenant_id, client_id and redirect_uri (set in App Registration)."
                )
        # DEFAULT, CLI, MANAGED_IDENTITY, INTERACTIVE_BROWSER validated at runtime.
        return self
