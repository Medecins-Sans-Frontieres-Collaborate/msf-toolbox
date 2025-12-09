from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import SecretStr

from msftoolbox.azure.auth.config import AuthConfig, Strategy


def test_factory_default__uses_default_credential(
    stub_azure: dict[str, Any], reload_factory
) -> None:
    """DEFAULT strategy: returns DefaultAzureCredential with authority passthrough."""
    cfg = AuthConfig(strategy=Strategy.DEFAULT, authority="https://login.example")
    _ = reload_factory.get_credential(cfg)

    klass = stub_azure["DefaultAzureCredential"]
    assert klass.call_count == 1
    assert klass.last_kwargs == {"authority": "https://login.example"}


def test_factory_cli__authority_passthrough(
    stub_azure: dict[str, Any], reload_factory
) -> None:
    cfg = AuthConfig(strategy=Strategy.CLI, authority="https://login.example")
    _ = reload_factory.get_credential(cfg)

    klass = stub_azure["AzureCliCredential"]
    assert klass.call_count == 1
    assert klass.last_kwargs == {"authority": "https://login.example"}


def test_factory_managed_identity__client_id_and_authority(
    stub_azure: dict[str, Any], reload_factory
) -> None:
    cfg = AuthConfig(
        strategy=Strategy.MANAGED_IDENTITY,
        client_id="cid",
        authority="https://login.example",
    )
    _ = reload_factory.get_credential(cfg)

    klass = stub_azure["ManagedIdentityCredential"]
    assert klass.call_count == 1
    assert klass.last_kwargs == {
        "client_id": "cid",
        "authority": "https://login.example",
    }


def test_factory_client_secret__unwraps_secret(
    stub_azure: dict[str, Any], reload_factory
) -> None:
    cfg = AuthConfig(
        strategy=Strategy.CLIENT_SECRET,
        tenant_id="t",
        client_id="c",
        client_secret=SecretStr("sekrit"),
        authority="https://login.example",
    )
    _ = reload_factory.get_credential(cfg)

    klass = stub_azure["ClientSecretCredential"]
    assert klass.call_count == 1
    assert klass.last_kwargs == {
        "tenant_id": "t",
        "client_id": "c",
        "client_secret": "sekrit",
        "authority": "https://login.example",
    }


def test_factory_client_certificate__path_and_optional_password(
    tmp_path: Path, stub_azure: dict[str, Any], reload_factory
) -> None:
    cert = tmp_path / "cert.pfx"
    cert.write_text("x")

    cfg = AuthConfig(
        strategy=Strategy.CLIENT_CERTIFICATE,
        tenant_id="t",
        client_id="c",
        certificate_path=cert,
        certificate_password=SecretStr("pw"),
        authority="https://login.example",
    )
    _ = reload_factory.get_credential(cfg)
    klass = stub_azure["CertificateCredential"]
    assert klass.call_count == 1
    assert klass.last_kwargs == {
        "tenant_id": "t",
        "client_id": "c",
        "certificate_path": str(cert),
        "password": "pw",
        "authority": "https://login.example",
    }

    # Now without password (None)
    cfg2 = AuthConfig(
        strategy=Strategy.CLIENT_CERTIFICATE,
        tenant_id="t",
        client_id="c",
        certificate_path=cert,
        authority="https://login.example",
    )
    _ = reload_factory.get_credential(cfg2)
    assert klass.call_count == 2
    assert klass.last_kwargs == {
        "tenant_id": "t",
        "client_id": "c",
        "certificate_path": str(cert),
        "password": None,
        "authority": "https://login.example",
    }


# def test_factory_workload_identity__token_file_path(
#     tmp_path: Path, stub_azure: dict[str, Any], reload_factory
# ) -> None:
#     token = tmp_path / "token.jwt"
#     token.write_text("jwt")

#     cfg = AuthConfig(
#         strategy=Strategy.WORKLOAD_IDENTITY,
#         tenant_id="t",
#         client_id="c",
#         federated_token_file=token,
#         authority="https://login.example",
#     )
#     _ = reload_factory.get_credential(cfg)

#     klass = stub_azure["WorkloadIdentityCredential"]
#     assert klass.call_count == 1
#     assert klass.last_kwargs == {
#         "tenant_id": "t",
#         "client_id": "c",
#         "token_file_path": str(token),
#         "authority": "https://login.example",
#     }


def test_factory_interactive_browser__fields(
    stub_azure: dict[str, Any], reload_factory
) -> None:
    cfg = AuthConfig(
        strategy=Strategy.INTERACTIVE_BROWSER,
        tenant_id="t",
        client_id="c",
        redirect_uri="http://localhost:8400",
        authority="https://login.example",
    )
    _ = reload_factory.get_credential(cfg)

    klass = stub_azure["InteractiveBrowserCredential"]
    assert klass.call_count == 1
    assert klass.last_kwargs == {
        "tenant_id": "t",
        "client_id": "c",
        "redirect_uri": "http://localhost:8400",
        "authority": "https://login.example",
    }


def test_factory_username_password__path_username_and_client_credentials(
    stub_azure: dict[str, Any], reload_factory
) -> None:
    cfg = AuthConfig(
        strategy=Strategy.USERNAME_PASSWORD,
        tenant_id="t",
        client_id="c",
        username="user",  # model uses Path; factory passes through (Path is accepted as str-like here)
        password=SecretStr("pw"),
        client_secret=SecretStr("client-cred"),
        authority="https://login.example",
    )
    _ = reload_factory.get_credential(cfg)

    klass = stub_azure["UsernamePasswordCredential"]
    # username comes out as a Path object; our stub records it verbatim
    assert klass.call_count == 1
    assert klass.last_kwargs == {
        "tenant_id": "t",
        "client_id": "c",
        "username": cfg.username,  # Path("user")
        "password": "pw",
        "authority": "https://login.example",
        "client_credentials": "client-cred",
    }
