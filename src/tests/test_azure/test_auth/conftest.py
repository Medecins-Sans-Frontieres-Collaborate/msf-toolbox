from __future__ import annotations

import importlib
import os
import sys
from types import ModuleType
from typing import Any, Iterator

import pytest


@pytest.fixture(autouse=True)
def clear_azure_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Remove AZURE_* vars to prevent cross-test leakage.

    Yields:
        Iterator[None]: Context manager semantics for pytest.
    """
    to_clear = [k for k in os.environ.keys()]
    for k in to_clear:
        monkeypatch.delenv(k, raising=False)
    yield


@pytest.fixture()
def stub_azure(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Inject minimal azure.* stubs so tests do not require azure packages.

    Returns:
        dict[str, Any]: Exposes stub classes for assertion (e.g., call kwargs).
    """
    # Base namespaces
    mod_azure = ModuleType("azure")
    mod_identity = ModuleType("azure.identity")
    mod_core = ModuleType("azure.core")
    mod_core_creds = ModuleType("azure.core.credentials")

    class TokenCredential:  # pragma: no cover - trivial stub
        """Base stub compatible with Azure credential typing."""

    mod_core_creds.TokenCredential = TokenCredential

    class _Recorder:
        """Factory to create recorder classes that capture init kwargs."""

        def __init__(self, name: str) -> None:
            self.name = name
            self.cls = self._make(name)

        @staticmethod
        def _make(name: str):
            class _C(TokenCredential):  # type: ignore[misc]
                last_args: tuple[Any, ...] | None = None
                last_kwargs: dict[str, Any] | None = None
                call_count: int = 0
                __name__ = name

                def __init__(self, *args: Any, **kwargs: Any) -> None:
                    type(self).last_args = args
                    type(self).last_kwargs = dict(kwargs)
                    type(self).call_count += 1

            _C.__qualname__ = name
            return _C

    # Create recorders for each credential type the factory uses
    names = [
        "DefaultAzureCredential",
        "AzureCliCredential",
        "ManagedIdentityCredential",
        "ClientSecretCredential",
        "CertificateCredential",
        "WorkloadIdentityCredential",
        "InteractiveBrowserCredential",
        "UsernamePasswordCredential",
    ]
    recorders = {n: _Recorder(n) for n in names}
    for n, rec in recorders.items():
        setattr(mod_identity, n, rec.cls)

    # Wire up module tree
    mod_azure.identity = mod_identity  # type: ignore[attr-defined]
    mod_azure.core = mod_core  # type: ignore[attr-defined]
    mod_core.credentials = mod_core_creds  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "azure", mod_azure)
    monkeypatch.setitem(sys.modules, "azure.identity", mod_identity)
    monkeypatch.setitem(sys.modules, "azure.core", mod_core)
    monkeypatch.setitem(sys.modules, "azure.core.credentials", mod_core_creds)

    # Import modules under test AFTER stubbing
    # If they were imported before, reload to bind to stubs.
    import msftoolbox.azure.auth.config as config  # noqa: F401
    import msftoolbox.azure.auth.factory as factory  # noqa: F401

    importlib.reload(factory)

    return {**{n: rec.cls for n, rec in recorders.items()}}


@pytest.fixture()
def reload_factory(stub_azure: dict[str, Any]) -> ModuleType:
    """Convenience fixture to return a freshly reloaded factory module.

    Args:
        stub_azure: Ensures stubs are installed first.

    Returns:
        ModuleType: The msftoolbox.azure.auth.factory module reloaded against stubs.
    """
    import importlib

    import msftoolbox.azure.auth.factory as factory  # type: ignore

    return importlib.reload(factory)
