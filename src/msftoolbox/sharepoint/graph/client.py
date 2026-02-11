from __future__ import annotations

import logging
import urllib.parse
import time
import random
import requests
from azure.core.credentials import AccessToken

from msftoolbox.azure.auth import scopes
from msftoolbox.azure.auth.config import AuthConfig
from msftoolbox.sharepoint.models import FileItem, FolderItem

from .context import build_graph_client
from .utils import convert_sharepoint_url, get_encoded_relative_path

logger = logging.getLogger(__name__)


class GraphFileClient:
    """Graph implementation of FileClient."""

    def __init__(self, site_url: str, *, auth: AuthConfig):
        """Initialize the grpah file client.

        Args:
            site_url: The URL of the SharePoint site.
            auth: Authentication configuration.
        """
        self._headers = {}
        self.select: str = None
        self.page_size: int = 500

        self._auth = auth
        self.graph_client, self._token_credential = build_graph_client(self._auth)
        self._access_token: AccessToken = self._refresh_token()
        if self._access_token:
            token = self._access_token.token
            self._headers = {"Authorization": f"Bearer {token}"}

        self._site_url: str = site_url
        self._site_id: str = self.get_site_id()

    def _refresh_token(self) -> AccessToken:
        """Return a new access token."""
        return self._token_credential.get_token(scopes.GRAPH_DEFAULT_SCOPE)

    def _build_request_params(
        self,
        select: str | None = None,
        expand: str | None = None,
        filter_: str | None = None,
        orderby: str | None = None,
        top: int | None = None,
        **kwargs
    ) -> str:
        """
        Build OData query parameters for Graph API requests.
        
        Args:
            select: Fields to select (e.g., "id,name,webUrl")
            expand: Fields to expand (e.g., "listItem($expand=fields($select=Manufacturer_Name))")
            filter_: OData filter expression (e.g., "lastModifiedDateTime gt 2026-01-01T00:00:00Z")
            orderby: Fields to order by (e.g., "lastModifiedDateTime desc")
            top: Number of items per page
            **kwargs: Additional OData parameters (e.g., skip=10, count=True)
        
        Returns:
            Query string with parameters
        """
        params = []
        
        if select:
            params.append(f"$select={select}")
        
        if expand:
            params.append(f"$expand={expand}")
        
        if filter_:
            params.append(f"$filter={filter_}")
        
        if orderby:
            params.append(f"$orderby={orderby}")
        
        if top is not None:
            params.append(f"$top={top}")
        
        # Handle additional OData parameters
        for key, value in kwargs.items():
            # Convert Python naming to OData (e.g., skip -> $skip)
            odata_key = f"${key}" if not key.startswith('$') else key
            params.append(f"{odata_key}={value}")
        
        return f"?{'&'.join(params)}" if params else ""
    
    def _fetch_with_retry(self, url: str, headers: dict):
        RETRY_STATUS_CODES = {429, 503, 504}
        MAX_RETRIES = 5
        BASE_DELAY = 1.0
        for attempt in range(1, MAX_RETRIES + 1):
            response = requests.get(url, headers=headers)
            if response.status_code < 400:
                return response.json()
            if response.status_code not in RETRY_STATUS_CODES:
                response.raise_for_status()
            # Retry logic
            retry_after = response.headers.get("Retry-After")

            if retry_after:
                delay = int(retry_after)
            else:
                delay = BASE_DELAY * (2 ** (attempt - 1))
                delay += random.uniform(0, 0.5)  # jitter
            if attempt == MAX_RETRIES:
                response.raise_for_status()
            logger.warning(
                "Graph API %s error. Retrying in %.1f seconds (attempt %d/%d)",
                response.status_code,
                delay,
                attempt,
                MAX_RETRIES,
            )
            time.sleep(delay)
        raise RuntimeError("Unreachable")

    def _paged_fetch(
        self,
        request_url: str,
        select: str | None = None,
        expand: str | None = None,
        filter_: str | None = None,
        orderby: str | None = None,
        top: int | None = None,
        **kwargs
    ):
        """
        Fetch paginated results from Graph API.
        
        Args:
            request_url: Base URL for the request
            select: Fields to select
            expand: Fields to expand
            filter_: OData filter expression
            orderby: Fields to order by
            top: Number of items per page
            **kwargs: Additional OData parameters
        
        Yields:
            Individual items from paginated response
        """
        def _fetch(initial: bool, next_link: str | None = None):
            if not initial and next_link:
                # nextLink already contains all query params
                return self._fetch_with_retry(next_link, self._headers)
            else:
                # Build URL with query params for initial request
                query_params = self._build_request_params(
                    select=select,
                    expand=expand,
                    filter_=filter_,
                    orderby=orderby,
                    top=top or self.page_size,
                    **kwargs
                )
                url = request_url + query_params
                return self._fetch_with_retry(url, self._headers)
            
        # Run first page 
        is_initial=True        
        page = _fetch(initial=is_initial)

        # Add log for first page
        if is_initial:
            page_number = 1
            logger.info("Fetched page %s", page_number)
            is_initial=False
        
        while True:
            next_link: str | None = page.get("@odata.nextLink", None)
            
            for item in page.get("value", []):
                yield item
            
            if not next_link:
                break
            
            logger.debug("Fetching next page via @odata.nextLink")
            page = _fetch(initial=is_initial, next_link=next_link)
            page_number += 1
            logger.info("Fetched page %s", page_number)


    @staticmethod
    def _map_file_properties(sp_file, keep_metadata: bool = True) -> FileItem:
        item = FileItem(
            name=sp_file.get("name"),
            server_relative_url=None,  # Graph does not work with server relative urls in the same way; should move to paths with ids.
            time_created=sp_file.get("createdDateTime"),
            time_last_modified=sp_file.get("lastModifiedDateTime"),
            extra=sp_file if keep_metadata else None,
        )
        return item

    @staticmethod
    def _map_folder_properties(sp_folder, keep_metadata: bool = True) -> FolderItem:
        item = FolderItem(
            name=sp_folder.get("name"),
            server_relative_url=None,  # Graph does not work with server relative urls in the same way; should move to paths with ids.
            time_created=sp_folder.get("createdDateTime"),
            time_last_modified=sp_folder.get("lastModifiedDateTime"),
            item_count=sp_folder.get("folder", {}).get("childCount"),
            extra=sp_folder if keep_metadata else None,
        )
        return item

    def get_site_id(self):
        formatted_url = convert_sharepoint_url(self._site_url)
        url = f"https://graph.microsoft.com/v1.0/sites/{formatted_url}"

        response = requests.get(url, headers=self._headers)
        response.raise_for_status()
        data = response.json()

        return data["id"]

    def get_library_id_from_url(self, server_relative_url: str):
        library_name = server_relative_url.strip("/").split("/")[0]

        # Encode name for comparison to web url, this avoids name differences
        # between graph and sharepoint (Documents vs Shared Documents)
        library_url = urllib.parse.quote(library_name)

        url = f"https://graph.microsoft.com/v1.0/sites/{self._site_id}/drives"

        for item in self._paged_fetch(url):
            name = item["name"]
            web_url = item["webUrl"]
            if (library_url in web_url) or (library_name in name):
                return item["id"]

        logger.warning(
            "Library %s could not be found in site %s.", library_name, self._site_url
        )
        return None

    def parse_server_relative_url(self, server_relative_url: str) -> tuple(
        str | None, str
    ):
        drive_id: str | None = self.get_library_id_from_url(server_relative_url)
        relative_path: str = get_encoded_relative_path(server_relative_url)

        return drive_id, relative_path

    def list_files_in_folder(
        self,
        folder_url: str,
        keep_metadata: bool = False,
        select: str | None = None,
        expand: str | None = None,
        filter_: str | None = None,
        orderby: str | None = None,
        page_size: int | None = None,
        **kwargs
    ) -> list[FileItem]:
        """
        Lists all files in a specified folder.
        
        Args:
            folder_url: The server-relative URL of the folder.
            select: Fields to select (e.g., "id,name,webUrl,file"). WARNING: If using select, make sure to include the file field.
            expand: Fields to expand (e.g., "listItem($expand=fields($select=Manufacturer_Name))")
            filter_: OData filter (e.g., "lastModifiedDateTime gt 2026-01-01T00:00:00Z")
            orderby: Order by clause (e.g., "lastModifiedDateTime desc")
            page_size: Number of items per page (overrides default)
            **kwargs: Additional OData parameters
        
        Returns:
            A list of file records in the folder.
        
        Examples:
            # Basic usage
            files = client.list_files_in_folder("/Documents")
            
            # With specific fields
            files = client.list_files_in_folder(
                "/Documents",
                select="id,name,webUrl",
                expand="listItem($expand=fields($select=Manufacturer_Name,Article_Tag))"
            )
            
            # With filtering and ordering
            files = client.list_files_in_folder(
                "/Documents",
                filter_="lastModifiedDateTime gt 2026-01-01T00:00:00Z",
                orderby="lastModifiedDateTime desc",
                page_size=50
            )
        """
        # Construct Graph API URL
        drive_id, relative_path = self.parse_server_relative_url(folder_url)
        path_segment = f":/{relative_path}:" if relative_path else ""
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root{path_segment}/children"
        
        items: list[FileItem] = []
        for item in self._paged_fetch(
            url,
            select=select,
            expand=expand,
            filter_=filter_,
            orderby=orderby,
            top=page_size,
            **kwargs
        ):
            if "file" in item or "listItem" in item:
                file_item: FileItem = self._map_file_properties(item)
                items.append(file_item)
        
        if not items:
            folder_name = folder_url.split("/")[-1] if "/" in folder_url else folder_url
            logger.info("No files were found in folder %s.", folder_name)
        
        return items

    def list_folders_in_folder(
        self,
        folder_url: str,
        keep_metadata: bool = False,
        select: str | None = None,
        expand: str | None = None,
        filter_: str | None = None,
        orderby: str | None = None,
        page_size: int | None = None,
        **kwargs
    ) -> list[FolderItem]:
        """
        Lists all folders in a specified folder.
        
        Args:
            folder_url: The server-relative URL of the folder.
            keep_metadata: If False, returns only name and server URL; 
                        if True, stores full properties in extra.
            select: Fields to select (e.g., "id,name,webUrl")
            expand: Fields to expand (e.g., "listItem($expand=fields($select=CustomColumn))")
            filter_: OData filter (e.g., "name eq 'Archive'")
            orderby: Order by clause (e.g., "name asc")
            page_size: Number of items per page (overrides default)
            **kwargs: Additional OData parameters
        
        Returns:
            A list of folder records in the folder.
        
        Examples:
            # Basic usage
            folders = client.list_folders_in_folder("/Documents")
            
            # With specific fields
            folders = client.list_folders_in_folder(
                "/Documents",
                select="id,name,webUrl",
                expand="listItem($expand=fields($select=CustomColumn))"
            )
            
            # With filtering and ordering
            folders = client.list_folders_in_folder(
                "/Documents",
                filter_="name ne 'Archive'",
                orderby="name asc",
                page_size=50
            )
        """
        # Construct Graph API URL
        drive_id, relative_path = self.parse_server_relative_url(folder_url)
        path_segment = f":/{relative_path}:" if relative_path else ""
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root{path_segment}/children"
        
        items: list[FolderItem] = []
        for item in self._paged_fetch(
            url,
            select=select,
            expand=expand,
            filter_=filter_,
            orderby=orderby,
            top=page_size,
            **kwargs
        ):
            if "folder" in item:
                folder_item: FolderItem = self._map_folder_properties(item)
                items.append(folder_item)
        
        if not items:
            folder_name = folder_url.split("/")[-1] if "/" in folder_url else folder_url
            logger.info("No folders were found in folder %s.", folder_name)
        
        return items
    def download_file(self, source_url: str, destination_file_path: str) -> None:
        """
        Downloads a file from SharePoint.

        Args:
            source_url (str): The server-relative URL of the file.
            local_file_path (str): The local path where the file will be saved.
        """
        # Construct Graph API URL
        drive_id, relative_path = self.parse_server_relative_url(source_url)
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{relative_path}:/content"
        response = requests.get(url, headers=self._headers)
        response.raise_for_status()

        # Load the file to the local file path
        with open(destination_file_path, "wb") as local_file:
            local_file.write(response.content)

        logger.info(f"Downloaded: {destination_file_path}")

    def upload_file(self, source_file_path: str, destination_url: str) -> None:
        """
        Uploads a file to the sharepoint folder.
        Files up to 250MB are accepted.

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
        if len(file_content) > 250 * 1024 * 1024:
            raise RuntimeError("File size exceeds 250MB limit for this upload method.")

        if not self.folder_exists(destination_url):
            raise ValueError("The destination folder does not exist.")

        else:
            # Construct Graph API URL
            file_name: str = source_file_path.split("/")[-1]
            drive_id, relative_path = self.parse_server_relative_url(destination_url)
            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{relative_path}/{file_name}:/content"

            response = requests.put(url, data=file_content, headers=self._headers)
            response.raise_for_status()
            item = response.json()

            logger.info(f"Uploaded: {source_file_path} to {destination_url}")
            item: FileItem = self._map_file_properties(item)

            return item

    def recursively_list_files(
        self, folder_url: str, keep_metadata: bool = False
    ) -> list[FileItem]:
        """
        Recursively expands folders and lists all files.

        Args:
            folder_url: The server-relative URL of the starting folder.
            keep_metadata: If false returns only the name and server url, else the full properties object
                is stored in extra.

        Returns:
            A list of all file items in the folder and its subfolders.
        """
        raise NotImplementedError(
            "recursively_list_files is not implemented for Graph backend yet."
        )

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
        raise NotImplementedError(
            "recursively_list_folders is not implemented for Graph backend yet."
        )

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
        raise NotImplementedError(
            "move_file_to_folder is not implemented for Graph backend yet."
        )

    def rename_file(self, file_url: str, new_file_name: str) -> None:
        """Renames the file at the specified server relative url

        Args:
            file_url: The server-relative URL of the file.
            new_file_name: The name of the new file without the path
        """
        raise NotImplementedError(
            "rename_file is not implemented for Graph backend yet."
        )

    def recycle_file(self, file_url: str) -> None:
        """Places a file in the recycle bin.

        Args:
            file_url: The server-relative URL of the file.
        """
        raise NotImplementedError(
            "recycle_file is not implemented for Graph backend yet."
        )

    def create_folder_if_not_exists(self, folder_url: str) -> FolderItem:
        """Creates a folder if it does not exist at the specified server-relative URL.

        Args:
            folder_url: The server-relative URL of the starting folder.

        Returns:
            The newly created folder or existing folder if it already existed
        """
        raise NotImplementedError(
            "create_folder_if_not_exists is not implemented for Graph backend yet."
        )

    def folder_exists(self, folder_url) -> bool:
        drive_id, relative_path = self.parse_server_relative_url(folder_url)
        url = (
            f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{relative_path}"
        )

        try:
            response = requests.get(url, headers=self._headers)
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError:
            return False
