# msftoolbox/sharepoint/fallback_file_client.py

from __future__ import annotations

from typing import Callable, ParamSpec, TypeVar

from msftoolbox.azure.auth.config import AuthConfig

from .graph.client import GraphFileClient
from .interfaces import FileClient
from .legacy.client import LegacyFileClient
from .models import FileItem

P = ParamSpec("P")
T = TypeVar("T")


class FallbackFileClient(FileClient):
    """File client that prefers Graph but falls back to legacy per feature.

    The primary backend is the Graph implementation; whenever a method is
    not supported and the Graph backend raises FeatureNotAvailableError,
    this client delegates the call to the legacy implementation.
    """

    def __init__(self, site_url: str, *, auth: AuthConfig) -> None:
        self._graph = GraphFileClient(site_url=site_url, auth=auth)
        self._legacy = LegacyFileClient(site_url=site_url, auth=auth)

    def _call_with_fallback(
        self,
        primary: Callable[P, T],
        fallback: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        try:
            return primary(*args, **kwargs)
        except NotImplementedError:
            return fallback(*args, **kwargs)

    def list_files_in_folder(
        self,
        folder_url: str,
        keep_metadata: bool = False,
    ) -> list[FileItem]:
        return self._call_with_fallback(
            self._graph.list_files_in_folder,
            self._legacy.list_files_in_folder,
            folder_url,
            keep_metadata=keep_metadata,
        )

    def list_folders_in_folder(
        self,
        folder_url: str,
        keep_metadata: bool = False,
    ) -> list[FileItem]:
        return self._call_with_fallback(
            self._graph.list_folders_in_folder,
            self._legacy.list_folders_in_folder,
            folder_url,
            keep_metadata=keep_metadata,
        )

    def recursively_list_files(
        self,
        folder_url: str,
        keep_metadata: bool = False,
    ) -> list[FileItem]:
        return self._call_with_fallback(
            self._graph.recursively_list_files,
            self._legacy.recursively_list_files,
            folder_url,
            keep_metadata=keep_metadata,
        )

    def recursively_list_folders(
        self,
        folder_url: str,
        keep_metadata: bool = False,
    ) -> list[FileItem]:
        return self._call_with_fallback(
            self._graph.recursively_list_folders,
            self._legacy.recursively_list_folders,
            folder_url,
            keep_metadata=keep_metadata,
        )

    def download_file(self, source_url: str, destination_file_path: str) -> None:
        return self._call_with_fallback(
            self._graph.download_file,
            self._legacy.download_file,
            source_url,
            destination_file_path,
        )

    def upload_file(self, source_file_path: str, destination_url: str) -> None:
        return self._call_with_fallback(
            self._graph.upload_file,
            self._legacy.upload_file,
            source_file_path,
            destination_url,
        )

    def move_file_to_folder(
        self,
        source_file_url: str,
        destination_folder_url: str,
        overwrite: bool = False,
    ) -> None:
        return self._call_with_fallback(
            self._graph.move_file_to_folder,
            self._legacy.move_file_to_folder,
            source_file_url,
            destination_folder_url,
            overwrite,
        )

    def rename_file(self, file_url: str, new_file_name: str) -> None:
        return self._call_with_fallback(
            self._graph.rename_file,
            self._legacy.rename_file,
            file_url,
            new_file_name,
        )

    def recycle_file(self, file_url: str) -> None:
        return self._call_with_fallback(
            self._graph.recycle_file,
            self._legacy.recycle_file,
            file_url,
        )

    def create_folder_if_not_exists(self, folder_url: str) -> None:
        return self._call_with_fallback(
            self._graph.create_folder_if_not_exists,
            self._legacy.create_folder_if_not_exists,
            folder_url,
        )

    def test_folder_existence(self, folder_url: str) -> bool:
        return self._call_with_fallback(
            self._graph.test_folder_existence,
            self._legacy.test_folder_existence,
            folder_url,
        )
