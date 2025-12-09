from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping


@dataclass
class FileItem:
    """Represents a file in SharePoint or OneDrive."""

    name: str
    server_relative_url: str
    time_created: datetime | None = None
    time_last_modified: datetime | None = None
    extra: Mapping[str, Any] | None = None


@dataclass
class FolderItem:
    """Represents a folder in SharePoint or OneDrive."""

    name: str
    server_relative_url: str
    time_created: datetime | None = None
    time_last_modified: datetime | None = None
    item_count: int | None = None
    extra: Mapping[str, Any] | None = None
