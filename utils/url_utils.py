import re
from typing import Optional


def get_id_from_url(url: str) -> Optional[str]:
    """
    Extracts the ID from the URL.

    Parameters:
    url (str): The URL to extract the ID from

    Returns:
    Optional[str]: The extracted ID if successful, None otherwise
    """
    pattern = r"https://(?:www\.)?zdf\.de/(?P<ID>[/\w-]+)\.html"
    match = re.match(pattern, url)
    return match["ID"] if match else None
