from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING
from warnings import warn

from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.files.file import File

from msftoolbox.azure.auth.config import AuthConfig
from msftoolbox.sharepoint.legacy.context import build_client_context
from msftoolbox.sharepoint.models import FileItem, FolderItem

if TYPE_CHECKING:
    from office365.sharepoint.files.collection import FileCollection
    from office365.sharepoint.files.file import File
    from office365.sharepoint.folders.collection import FolderCollection
    from office365.sharepoint.folders.folder import Folder

logger = logging.getLogger(__name__)


class LegacyFileClient:
    """Legacy Office365-based implementation of FileClient."""

    def __init__(self, site_url: str, *, auth: AuthConfig):
        """Initialize the legacy file client.

        Args:
            site_url: The URL of the SharePoint site.
            auth: Authentication configuration.
        """
        self._site_url = site_url
        self._auth = auth
        # Context scope requires scheme, whereas client requires no scheme
        self._absolute_site_url = (
            f"https://{site_url}" if not site_url.startswith("http") else site_url
        )
        self.context: ClientContext = build_client_context(
            site_url=self._absolute_site_url, auth_config=auth
        )

    @staticmethod
    def _map_file_properties(sp_file: "File", keep_metadata: bool = True) -> FileItem:
        props = sp_file.properties
        item = FileItem(
            name=props.get("Name"),
            server_relative_url=props.get("ServerRelativeUrl"),
            time_created=props.get("TimeCreated"),
            time_last_modified=props.get("TimeLastModified"),
            extra=props if keep_metadata else None,
        )
        return item

    @staticmethod
    def _map_folder_properties(
        sp_folder: "Folder", keep_metadata: bool = True
    ) -> FolderItem:
        props = sp_folder.properties
        item = FolderItem(
            name=props.get("Name"),
            server_relative_url=props.get("ServerRelativeUrl"),
            time_created=props.get("TimeCreated"),
            time_last_modified=props.get("TimeLastModified"),
            item_count=props.get("ItemCount"),
            extra=props if keep_metadata else None,
        )
        return item

    def list_files_in_folder(
        self, folder_url: str, keep_metadata: bool = False
    ) -> list[FileItem]:
        """
        Lists all files in a specified folder.

        Args:
            folder_url: The server-relative URL of the folder (/Site_Name/Subsite_Name/Folder_Name/File_Name).
            keep_metadata: If false returns only the name and server url, else the full properties object
                is stored in extra:
                'CheckInComment', 'CheckOutType', 'ContentTag', 'CustomizedPageStatus', 'ETag', 'Exists',
                'ExistsAllowThrowForPolicyFailures', 'ExistsWithException', 'IrmEnabled', 'Length', 'Level',
                'LinkingUri', 'LinkingUrl', 'MajorVersion', 'MinorVersion', 'Name', 'ServerRelativeUrl',
                'TimeCreated', 'TimeLastModified', 'Title', 'UIVersion', 'UIVersionLabel', 'UniqueId'
        Returns:
            A list of file records in the folder.
        """
        # Get the folder
        folder: "Folder" = self.context.web.get_folder_by_server_relative_url(
            folder_url
        )

        # List the files in the folder
        files: "FileCollection" = folder.files
        self.context.load(files)
        self.context.execute_query_with_incremental_retry()

        # If the keep_metadata attribute is True then keep
        # all properties else subset for commonly used ones
        items: list[FileItem] = []
        for sp_file in files:
            item: FileItem = self._map_file_properties(sp_file, keep_metadata)
            items.append(item)
        return items

    def list_folders_in_folder(
        self, folder_url: str, keep_metadata: bool = False
    ) -> list[FolderItem]:
        """
        Lists all files in a specified folder.

        Args:
            folder_url: The server-relative URL of the folder.
            keep_metadata: If false returns only the name and server url, else the full properties object:
                'Exists', 'ExistsAllowThrowForPolicyFailures', 'ExistsWithException', 'IsWOPIEnabled', 'ItemCount', 'Name',
                'ProgID', 'ServerRelativeUrl', 'TimeCreated', 'TimeLastModified', 'UniqueId', 'WelcomePage'

        Returns:
            A list of folder records in the folder.
        """
        # Get the folder
        folder: "Folder" = self.context.web.get_folder_by_server_relative_url(
            folder_url
        )

        # List folders in the folder
        folders: "FolderCollection" = folder.folders
        self.context.load(folders)
        self.context.execute_query_with_incremental_retry()

        # If the keep_metadata attribute is True then keep
        # all properties else subset for commonly used ones
        items: list[FileItem] = []
        for sp_folder in folders:
            item: FolderItem = self._map_folder_properties(sp_folder, keep_metadata)
            items.append(item)
        return items

    def download_file(self, source_url: str, destination_file_path: str) -> None:
        """
        Downloads a file from SharePoint.

        Args:
            source_url (str): The server-relative URL of the file.
            local_file_path (str): The local path where the file will be saved.
        """
        # Get the file
        file: "File" = self.context.web.get_file_by_server_relative_url(source_url)

        self.context.load(file)
        self.context.execute_query_with_incremental_retry()

        # Load the file to the local file path
        with open(destination_file_path, "wb") as local_file:
            file.download(local_file).execute_query_with_incremental_retry()

        logger.info(f"Downloaded: {destination_file_path}")

    def upload_file(self, source_file_path: str, destination_url: str) -> FileItem:
        """
        Uploads a file to the sharepoint folder.
        Files up to 4MB are accepted.

        Args:
            source_file_path: The local path of the file too upload.
            destination_url: The server-relative URL of the folder destination.

        Returns:
            Uploaded file item.
        """
        # Open the file and store the content
        with open(source_file_path, "rb") as content_file:
            file_content = content_file.read()

        # Check if file exceeds size limit
        if len(file_content) > 4 * 1024 * 1024:
            raise RuntimeError("File size exceeds 4MB limit for this upload method.")

        if not self.folder_exists(destination_url):
            raise ValueError("The destination folder does not exist")
        else:
            # Get the Sharepoint target folder
            target_folder = self.context.web.get_folder_by_server_relative_url(
                destination_url
            )
            target_folder.get()
            target_folder.execute_query_with_incremental_retry()

            # Get the file name based on the source name
            name = Path(source_file_path).name

            # Upload
            file: File = target_folder.upload_file(name, file_content)
            self.context.execute_query_with_incremental_retry()

            logger.info(f"Uploaded: {source_file_path} to {destination_url}")
            item: FileItem = self._map_file_properties(file)

            return item

    def recursively_list_files(
        self, folder_url: str, keep_metadata: bool = False
    ) -> list[FileItem]:
        """
        Recursively expands folders and lists all files.

        Args:
            folder_url: The server-relative URL of the starting folder.
            keep_metadata: If false returns only the server url, else the full properties object
                is stored in extra:
                'CheckInComment', 'CheckOutType', 'ContentTag', 'CustomizedPageStatus', 'ETag', 'Exists',
                'ExistsAllowThrowForPolicyFailures', 'ExistsWithException', 'IrmEnabled', 'Length', 'Level',
                'LinkingUri', 'LinkingUrl', 'MajorVersion', 'MinorVersion', 'Name', 'ServerRelativeUrl',
                'TimeCreated', 'TimeLastModified', 'Title', 'UIVersion', 'UIVersionLabel', 'UniqueId'

        Returns:
            A list of all file items in the folder and its subfolders.
        """
        # Get the folders in the root folder
        folders: list[FolderItem] = self.list_folders_in_folder(folder_url)

        # Get all the files in the folder
        all_files = []
        for subfolder in folders:
            subfolder_url = subfolder.server_relative_url
            all_files.extend(self.recursively_list_files(subfolder_url, keep_metadata))

        all_files.extend(self.list_files_in_folder(folder_url, keep_metadata))

        return all_files

    def recursively_list_folders(
        self, folder_url: str, keep_metadata: bool = False
    ) -> list[FolderItem]:
        """
        Recursively expands folders and lists all files.

        Args:
            folder_url: The server-relative URL of the starting folder.
            keep_metadata: If false returns only the server url, else the full properties object
                is stored in extra:
                'Exists', 'ExistsAllowThrowForPolicyFailures', 'ExistsWithException', 'IsWOPIEnabled', 'ItemCount', 'Name',
                'ProgID', 'ServerRelativeUrl', 'TimeCreated', 'TimeLastModified', 'UniqueId', 'WelcomePage'

        Returns:
            A list of all folder items and their subfolders.
        """
        # Get the folders in the root folder
        folders: list[FolderItem] = self.list_folders_in_folder(folder_url)

        # Get all the files in the folder
        all_folders: list[FolderItem] = []
        for subfolder in folders:
            subfolder_url = subfolder.server_relative_url
            all_folders.extend(
                self.recursively_list_folders(subfolder_url, keep_metadata)
            )

        all_folders.extend(self.list_folders_in_folder(folder_url, keep_metadata))

        return all_folders

    def move_file_to_folder(
        self, source_file_url: str, destination_folder_url: str, overwrite: bool = False
    ) -> FileItem:
        """
        Moves a file from the specified url to a destination folder.
        Important: The destination_folder_url should not include the name.

        Args:
            source_file_url: The local path of the file too upload.
            destination_url: The server-relative URL of the folder destination.
            overwrite: Determines the behaviour if a file is at the specified destination.

        Returns:
            The file item representing the moved file.
        """

        file: File = self.context.web.get_file_by_server_relative_url(source_file_url)

        file.moveto(destination_folder_url, int(overwrite))
        self.context.execute_query_with_incremental_retry()

        item: FileItem = self._map_file_properties(file)
        return item

    def rename_file(self, file_url: str, new_file_name: str) -> None:
        """Renames the file at the specified server relative url

        Args:
            file_url: The server-relative URL of the file.
            new_file_name: The name of the new file without the path
        """
        if Path(new_file_name).name != new_file_name:
            raise ValueError("new_file_name should not contain a path.")

        file: File = self.context.web.get_file_by_server_relative_url(file_url)

        file.rename(new_file_name)
        self.context.execute_query_with_incremental_retry()

        return None

    def recycle_file(self, file_url: str) -> None:
        """Places a file in the recycle bin.

        Args:
            file_url: The server-relative URL of the file.
        """

        file: File = self.context.web.get_file_by_server_relative_url(file_url)

        file.recycle()
        self.context.execute_query_with_incremental_retry()

        return None

    def create_folder_if_not_exists(self, folder_url: str) -> FolderItem:
        """Creates a folder if it does not exist at the specified server-relative URL.

        Args:
            folder_url: The server-relative URL of the starting folder.

        Returns:
            The newly created folder or existing folder if it already existed
        """
        if self.folder_exists(folder_url):
            logger.warning("Folder exits already.")
            folder: Folder = self.context.web.get_folder_by_server_relative_url(
                folder_url
            )
            folder.get().execute_query_with_incremental_retry()

        else:
            logger.info("Creating folder at %s.", folder_url)
            folder = (
                self.context.web.ensure_folder_path(folder_url)
                .get()
                .execute_query_with_incremental_retry()
            )
        item: FolderItem = self._map_file_properties(folder)
        return item

    def folder_exists(self, folder_url: str) -> bool:
        """Tests for the existence of a folder at the server-relative URL.

        Args:
            folder_url: The server-relative URL of the starting folder.

        Returns:
            True if the folder exists, False otherwise.
        """
        folder_test: Folder = (
            self.context.web.get_folder_by_server_relative_path(folder_url)
            .get()
            .execute_query_with_incremental_retry()
        )

        return folder_test.properties.get("Exists", False)

    def test_folder_existence(self, folder_url) -> bool:
        """Tests for the existence of a folder at the server-relative URL.

        Args:
            folder_url (str): The server-relative URL of the starting folder.

        Returns:
            str: The server-relative URL of the starting folder.
        """
        warn(
            "test_folder_existence is deprecated; use folder_exists instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.folder_exists(folder_url)
