import urllib.parse


def convert_sharepoint_url(url: str) -> str:
    # Remove the scheme (http:// or https://)
    if url.startswith("https://"):
        url = url[len("https://") :]
    elif url.startswith("http://"):
        url = url[len("http://") :]

    # Replace the first '/' with ':/' to match the desired format
    parts = url.split("/", 1)
    if len(parts) == 2:
        return f"{parts[0]}:/{parts[1]}"
    else:
        return f"{parts[0]}:/"


def get_encoded_relative_path(server_relative_url: str) -> str:
    # The relative path must be encoded for special characters
    drive_relative_url = server_relative_url.strip("/").split("/", 1)
    return urllib.parse.quote(drive_relative_url[1]) if len(drive_relative_url) > 1 else ""
