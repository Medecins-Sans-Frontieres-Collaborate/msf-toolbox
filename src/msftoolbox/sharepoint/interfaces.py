from __future__ import annotations

from typing import Protocol

from .models import FileItem, FolderItem


class FileClient(Protocol):
    """Protocol for file and folder operations on a SharePoint site.

    Implementations may use the legacy Office365 API, Microsoft Graph,
    or other providers. All methods should operate on a single site
    identified at construction time.
    """

    def list_files_in_folder(
        self,
        folder_url: str,
        keep_metadata: bool = False,
    ) -> list[FileItem]:
        """List files in a folder."""
        raise NotImplementedError

    def list_folders_in_folder(
        self,
        folder_url: str,
        keep_metadata: bool = False,
    ) -> list[FolderItem]:
        """List folders in a folder, represented as FileItem with folder semantics."""
        raise NotImplementedError

    def recursively_list_files(
        self,
        folder_url: str,
        keep_metadata: bool = False,
    ) -> list[FileItem]:
        """Recursively list files under a folder."""
        raise NotImplementedError

    def recursively_list_folders(
        self,
        folder_url: str,
        keep_metadata: bool = False,
    ) -> list[FolderItem]:
        """Recursively list folders under a folder."""
        raise NotImplementedError

    def download_file(self, source_url: str, destination_file_path: str) -> None:
        """Download a file to a local path."""
        raise NotImplementedError

    def upload_file(self, source_file_path: str, destination_url: str) -> None:
        """Upload a local file to a folder URL."""
        raise NotImplementedError

    def move_file_to_folder(
        self,
        source_file_url: str,
        destination_folder_url: str,
        overwrite: bool = False,
    ) -> FileItem:
        """Move a file to another folder."""
        raise NotImplementedError

    def rename_file(self, file_url: str, new_file_name: str) -> None:
        """Rename a file in place."""
        raise NotImplementedError

    def recycle_file(self, file_url: str) -> None:
        """Move a file into the recycle bin."""
        raise NotImplementedError

    def create_folder_if_not_exists(self, folder_url: str) -> FolderItem:
        """Create a folder if it does not exist."""
        raise NotImplementedError

    def test_folder_existence(self, folder_url: str) -> bool:
        """Return True if the folder exists."""
        raise NotImplementedError
