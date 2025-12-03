# SharePointClient

## Overview

`SharePointClient` is a Python class designed to interact with the Office365 SharePoint API. It provides methods for authenticating, listing files and folders, downloading, uploading, moving, renaming, and recycling files, as well as creating folders.

## Features

- **Authentication**: Easily authenticate with SharePoint using your credentials.
- **File and Folder Management**: List, download, upload, move, rename, and recycle files. List and create folders.
- **Recursive Operations**: Recursively list files and folders within a directory. Please note that certain characters in URLs can cause issues such as "#".

## Usage

### Initialization

The SharePointClient takes two main arguments for initialisation, the `site_url` and `auth` method.
```python
from msftoolbox.sharepoint import SharePointClient

client = SharePointClient(
    site_url="https://your-site-url",
    auth=AuthConfig()
)
```

Initialising the client this way will force it to prefer Microsoft Graph whenever possible, and fall back to SharePoint Rest API otherwise. To change this behaviour, you can
specify a `backend`:
```python
from msftoolbox.sharepoint import SharePointClient

client = SharePointClient(
    site_url="https://your-site-url",
    auth=AuthConfig(),
    backend="graph",  # Options are graph, legacy, auto (default)
)
```

There are two options for setting your authentication method (more detailed explanations and documentation can be found [here](../azure/auth/README.md)):
1. Via a `.env` file
2. Inline within your code

#### Define authentication in .env
The default auth method will try first try pull from your local `.env` file:
1. Create new file in your root directory and name is `.env`
2. In this file, copy the following and pass the values you want and remove the others:
    ```bash
    STRATEGY="interactive_browser"
    AZURE_TENANT_ID=''
    AZURE_CLIENT_ID=''
    AZURE_CLIENT_SECRET=''
    CERTIFICATE_PATH=''
    USERNAME=''
    PASSWORD=''
    ```

#### Inline

Available strategies can be found [here](../azure/auth/config.py#L10), and can either be imported or you can type the string:

```python
Strategy.DEFAULT = "default"
Strategy.CLI = "cli"
Strategy.MANAGED_IDENTITY = "managed_identity"
Strategy.CLIENT_SECRET = "client_secret"
Strategy.CLIENT_CERTIFICATE = "client_certificate"
Strategy.INTERACTIVE_BROWSER = "interactive_browser"
Strategy.USERNAME_PASSWORD = "username_password"  # Deprecated 30 September, 2025
```

##### Using Client ID and Secret 
```python
from msftoolbox.azure.auth import AuthConfig
from msftoolbox.sharepoint import SharePointClient

client = SharePointClient(
    site_url="https://your-site-url",
    auth=AuthConfig(
        strategy="client_secret",
        tenant_id="your-tenant-id",
        client_id="your-client-id",
        client_secret="your-client-secret",
    )
)
```

##### Using Username and Password
Fails for MFA enabled accounts.
Requires an app registration with delegated Sharepoint API permissions.

```python
from msftoolbox.azure.auth import AuthConfig, Strategy
from msftoolbox.sharepoint import SharePointClient

client = SharePointClient(
    site_url="https://your-site-url",
    auth=AuthConfig(
        strategy=Strategy.USERNAME_PASSWORD,
        tenant_id="your-tenant-id",
        client_id="your-client-id",
        client_secret="your-client-secret",
        username="your-username",
        password="your-password",
    )
)
```

##### Using Interactive login
Requires an app registration with delegated Sharepoint API permissions.

```python
from msftoolbox.azure.auth import AuthConfig, Strategy
from msftoolbox.sharepoint import SharePointClient

client = SharePointClient(
    site_url="https://your-site-url",
    auth=AuthConfig(
        strategy=Strategy.INTERACTIVE_BROWSER,
        tenant_id="your-tenant-id",
        client_id="your-client-id",
        redirect_uri="http://localhost:8400",  # Redirect uri should be set in the app registration, but usually defaults to this
    )
)
```

##### Using Certificate login
Requires an app registration with Sites.Selected Application permission and site membership.
For detailed instructions, reach out the the OCA AI team. 

```python
from msftoolbox.azure.auth import AuthConfig, Strategy
from msftoolbox.sharepoint import SharePointClient

client = SharePointClient(
    site_url="https://your-site-url",
    auth=AuthConfig(
        strategy=Strategy.CLIENT_CERTIFICATE,
        tenant_id="your-tenant-id",
        client_id="your-client-id",
        certificate_path="path/to/certificate",
    )
)
```


### Methods

#### List Files in a Folder

```python
files = client.files.list_files_in_folder(
    folder_url="/path/to/folder"
    )
```

#### List Folders in a Folder

```python
folders = client.files.list_folders_in_folder(
    folder_url="/path/to/folder"
    )
```

#### Download a File

```python
client.files.download_file(
    source_url="/path/to/file", 
    destination_file_path="local/path/to/save"
    )
```

#### Upload a File

```python
client.files.upload_file(
    source_file_path="local/path/to/file", 
    destination_url="/path/to/destination/folder"
    )
```

#### Move a File

```python
client.files.move_file_to_folder(
    source_file_url="/path/to/file", 
    destination_folder_url="/path/to/destination/folder"
    )
```

#### Rename a File

```python
client.files.rename_file(
    file_url="/path/to/file", 
    new_file_name="new-name.txt"
    )
```

#### Recycle a File

```python
client.files.recycle_file(
    file_url="/path/to/file"
    )
```

#### Create a Folder if Not Exists

```python
client.files.create_folder_if_not_exists(
    folder_url="/path/to/folder"
    )
```

#### Test Folder Existence

```python
exists = client.files.folder_exists(
    folder_url="/path/to/folder"
    )
```

### Models
Any client methods that work with files or folders will generally return either a FileItem or FolderItem object. This makes it easier to work with the items you are retrieving, and prevents typos in manually typed strings when trying to retrieve core properties.

Caller example:
```python
from msftoolbox.sharepoint.models import FileItem, FolderItem

files = client.files.list_files_in_folder(
    folder_url="/path/to/folder"
    )

folders = client.files.list_folders_in_folder(
    folder_url="/path/to/folder"
    )

for item in files + folders:
    name = item.name
    if isinstance(item, FolderItem):
        # It's a folder; call item_count on object
        count = item.item_count
        print(f"[Folder] {name} - contains {count} items")
    elif isinstance(item, FileItem):
        size = item.extra.get('size', 0)
        print(f"[File] {name} - size {size} bytes") 
```

#### FileItem
Attributes:
- name
- server_relative_url
- time_created
- time_last_modified
- extra (see [`keep_metadata` parameter](#keep_metadata-parameter))

#### FolderItem
Attributes:
- name
- server_relative_url
- time_created
- time_last_modified
- item_count
- extra (see [`keep_metadata` parameter](#keep_metadata-parameter))

### `keep_metadata` Parameter

The `keep_metadata` parameter is used in methods that list files or folders, such as `list_files_in_folder` and `list_folders_in_folder`. It determines whether the extra properties retrieved for the item are returned in the models `extra` attribute.

#### Usage

- **`keep_metadata=False`**: 
  - Returns a simplified list containing only essential information, such as the name, server-relative URL, and last modified time of each file or folder.
  - This option is useful when you need a quick overview without detailed properties.

- **`keep_metadata=True`**: 
  - Returns the full properties object for each file or folder, including all available metadata.
  - This option is ideal when you need comprehensive information about each item, such as size, author, or custom metadata fields.

> :warning: **One note to be aware of is the difference between using Graph and SharePoint Rest API for working with SharePoint Online as they return different properties with different names. For example, Graph does not return or work with server relative urls.**
