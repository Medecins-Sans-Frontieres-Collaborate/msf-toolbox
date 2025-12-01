"""Backwards-compatible file client façade.

This module preserves the legacy SharePointFileClient entrypoint but
internally delegates to SharePointClient.files.
"""

from __future__ import annotations

from msftoolbox.azure.auth.config import AuthConfig

from .client import SharePointClient
from .models import FileItem


class SharePointFileClient:
    """Backwards-compatible file client façade.

    This class delegates all operations to SharePointClient.files.
    It is deprecated in favor of SharePointClient.
    """

    def __init__(
        self,
        site_url: str,
        *,
        auth: AuthConfig | None = None,
        # Same legacy kwargs as before (still deprecated):
        username: str | None = None,
        password: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        interactive_auth: bool | None = None,
        tenant_id: str | None = None,
        thumbprint: str | None = None,
        certificate_path: str | None = None,
    ) -> None:
        self._core = SharePointClient(
            site_url=site_url,
            auth=auth,
            username=username,
            password=password,
            client_id=client_id,
            client_secret=client_secret,
            interactive_auth=interactive_auth,
            tenant_id=tenant_id,
            thumbprint=thumbprint,
            certificate_path=certificate_path,
        )
        self._files = self._core.files

    # Delegate methods:

    def list_files_in_folder(
        self,
        folder_url: str,
        keep_metadata: bool = False,
    ) -> list[FileItem]:
        return self._files.list_files_in_folder(folder_url, keep_metadata)

    def list_folders_in_folder(
        self,
        folder_url: str,
        keep_metadata: bool = False,
    ) -> list[FileItem]:
        return self._files.list_folders_in_folder(folder_url, keep_metadata)

    def recursively_list_files(
        self,
        folder_url: str,
        keep_metadata: bool = False,
    ) -> list[FileItem]:
        return self._files.recursively_list_files(folder_url, keep_metadata)

    def recursively_list_folders(
        self,
        folder_url: str,
        keep_metadata: bool = False,
    ) -> list[FileItem]:
        return self._files.recursively_list_folders(folder_url, keep_metadata)

    def download_file(self, source_url: str, destination_file_path: str) -> None:
        self._files.download_file(source_url, destination_file_path)

    def upload_file(self, source_file_path: str, destination_url: str) -> None:
        self._files.upload_file(source_file_path, destination_url)

    def move_file_to_folder(
        self,
        source_file_url: str,
        destination_folder_url: str,
        overwrite: bool = False,
    ) -> None:
        self._files.move_file_to_folder(
            source_file_url, destination_folder_url, overwrite
        )

    def rename_file(self, file_url: str, new_file_name: str) -> None:
        self._files.rename_file(file_url, new_file_name)

    def recycle_file(self, file_url: str) -> None:
        self._files.recycle_file(file_url)

    def create_folder_if_not_exists(self, folder_url: str) -> None:
        self._files.create_folder_if_not_exists(folder_url)

    def test_folder_existence(self, folder_url: str) -> bool:
        return self._files.test_folder_existence(folder_url)
