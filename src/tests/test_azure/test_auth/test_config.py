from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr

from msftoolbox.azure.auth.config import AuthConfig, Strategy


def _touch(tmp_path: Path, name: str) -> Path:
    """Create a file in tmp_path and return its Path."""
    p = tmp_path / name
    p.write_text("x")
    return p


def test_path_validator__raises_on_missing_paths(tmp_path: Path) -> None:
    """certificate_path and federated_token_file must exist if provided."""
    with pytest.raises(ValueError, match="Path does not exist"):
        AuthConfig(
            strategy=Strategy.CLIENT_CERTIFICATE,
            certificate_path=tmp_path / "nope",
            tenant_id="t",
            client_id="c",
        )

    with pytest.raises(ValueError, match="Path does not exist"):
        AuthConfig(
            strategy=Strategy.WORKLOAD_IDENTITY,
            federated_token_file=tmp_path / "nope",
            tenant_id="t",
            client_id="c",
        )


def test_client_secret_strategy__requires_all_fields() -> None:
    """CLIENT_SECRET must have tenant_id, client_id, client_secret."""
    with pytest.raises(ValueError, match="client_secret requires"):
        AuthConfig(strategy=Strategy.CLIENT_SECRET, tenant_id="t", client_id="c")

    cfg = AuthConfig(
        strategy=Strategy.CLIENT_SECRET,
        tenant_id="t",
        client_id="c",
        client_secret=SecretStr("s"),
    )
    assert cfg.client_secret and cfg.client_secret.get_secret_value() == "s"


def test_client_certificate_strategy__requires_fields(tmp_path: Path) -> None:
    """CLIENT_CERTIFICATE must have tenant_id, client_id, certificate_path."""
    with pytest.raises(ValueError, match="client_certificate requires"):
        AuthConfig(strategy=Strategy.CLIENT_CERTIFICATE, tenant_id="t", client_id="c")

    cert = _touch(tmp_path, "cert.pfx")
    cfg = AuthConfig(
        strategy=Strategy.CLIENT_CERTIFICATE,
        tenant_id="t",
        client_id="c",
        certificate_path=cert,
        certificate_password=SecretStr("pw"),
    )
    assert cfg.certificate_path == cert
    assert (
        cfg.certificate_password and cfg.certificate_password.get_secret_value() == "pw"
    )


def test_workload_identity_strategy__requires_fields(tmp_path: Path) -> None:
    """WORKLOAD_IDENTITY must have tenant_id, client_id, federated_token_file."""
    with pytest.raises(ValueError, match="workload_identity requires"):
        AuthConfig(strategy=Strategy.WORKLOAD_IDENTITY, tenant_id="t", client_id="c")

    token = _touch(tmp_path, "token.jwt")
    cfg = AuthConfig(
        strategy=Strategy.WORKLOAD_IDENTITY,
        tenant_id="t",
        client_id="c",
        federated_token_file=token,
    )
    assert cfg.federated_token_file == token


def test_username_password_strategy__requires_fields() -> None:
    """USERNAME_PASSWORD must include tenant_id, client_id, username, password, client_secret."""
    with pytest.raises(ValueError, match="username_password requires"):
        AuthConfig(strategy=Strategy.USERNAME_PASSWORD, tenant_id="t", client_id="c")

    cfg = AuthConfig(
        strategy=Strategy.USERNAME_PASSWORD,
        tenant_id="t",
        client_id="c",
        username="user",  # parsed to Path by the model type
        password=SecretStr("pw"),
        client_secret=SecretStr("client-cred"),
    )
    # username typed as Path in model; ensure it parsed, but value survives
    # This also highlights a likely refactor need in notes.
    assert str(cfg.username) == "user"  # Path("user") -> "user"
    assert cfg.password and cfg.password.get_secret_value() == "pw"
    assert cfg.client_secret and cfg.client_secret.get_secret_value() == "client-cred"


def test_env_aliases__client_id_and_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate env alias reading for client_id and authority host."""
    monkeypatch.setenv("AUTH_STRATEGY", "managed_identity")
    monkeypatch.setenv("MANAGED_IDENTITY_CLIENT_ID", "abc-123")
    monkeypatch.setenv("AUTHORITY_HOST", "https://login.microsoftonline.com")

    cfg = AuthConfig()
    assert cfg.strategy is Strategy.MANAGED_IDENTITY
    assert cfg.client_id == "abc-123"
    assert cfg.authority == "https://login.microsoftonline.com"
