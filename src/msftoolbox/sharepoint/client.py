from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from msftoolbox.azure.auth.config import AuthConfig

from .auth_legacy import _auth_from_legacy_kwargs
from .fallback_client import FallbackFileClient
from .graph.client import GraphFileClient
from .interfaces import FileClient
from .legacy.client import LegacyFileClient

logger = logging.getLogger(__name__)

Backend = Literal["graph", "legacy", "auto"]


@dataclass
class SharePointClient:
    """Core SharePoint client for a specific site.

    This client owns authentication and backend selection, and exposes
    sub-clients for operations on files (and later folders, libraries, etc.).
    """

    _site_url: str
    _auth: AuthConfig
    _backend: Backend
    _files: FileClient

    def __init__(
        self,
        site_url: str,
        *,
        auth: AuthConfig | None = None,
        backend: Backend = "auto",
        # Legacy (deprecated) parameters - pass-through to _auth_from_legacy_kwargs:
        username: str | None = None,
        password: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        interactive_auth: bool | None = None,
        tenant_id: str | None = None,
        thumbprint: str | None = None,
        certificate_path: str | None = None,
    ) -> None:
        """Initialize the SharePoint client for a site.

        Args:
            site_url: The URL of the SharePoint site.
            auth: Authentication configuration. If omitted, legacy keyword
                arguments may be used (deprecated).
            backend: Which backend to use.
            username: Deprecated legacy username.
            password: Deprecated legacy password.
            client_id: Deprecated legacy client ID.
            client_secret: Deprecated legacy client secret.
            interactive_auth: Deprecated interactive auth flag.
            tenant_id: Deprecated Azure tenant ID.
            thumbprint: Deprecated certificate thumbprint.
            certificate_path: Deprecated certificate path.
        """
        self._site_url = site_url
        self._backend = backend

        if auth is None:
            auth = _auth_from_legacy_kwargs(
                username=username,
                password=password,
                client_id=client_id,
                client_secret=client_secret,
                interactive_auth=interactive_auth,
                tenant_id=tenant_id,
                thumbprint=thumbprint,
                certificate_path=certificate_path,
            )

        self._auth = auth
        self._files = self._create_file_backend(backend)

    @property
    def files(self) -> FileClient:
        """Return the file client for this site.

        The returned object implements the :class:`FileClient` protocol
        and may be backed by either the Graph or legacy implementation,
        depending on the configured backend.
        """
        return self._files

    def _create_file_backend(self, backend: Backend) -> FileClient:
        """Instantiate the file backend for the configured site and auth.

        Args:
            backend: Backend selector. See :meth:`__init__`.

        Returns:
            An instance implementing :class:`FileClient`.

        Raises:
            ValueError: If an unknown backend is specified.
        """
        if backend == "legacy":
            return LegacyFileClient(site_url=self._site_url, auth=self._auth)

        if backend == "graph":
            return GraphFileClient(site_url=self._site_url, auth=self._auth)

        if backend == "auto":
            # For now, "auto" is equivalent to "graph". If you later want
            # to implement feature-based fallback, do it here.
            return FallbackFileClient(site_url=self._site_url, auth=self._auth)

        raise ValueError(f"Unsupported backend: {backend!r}")
