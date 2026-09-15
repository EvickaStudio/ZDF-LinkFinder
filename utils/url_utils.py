import re
from typing import Optional
from urllib.parse import urlparse, urlunparse


def get_id_from_url(url: str) -> Optional[str]:
    """
    Extracts the ID from the URL.

    Parameters:
    url (str): The URL to extract the ID from

    Returns:
    Optional[str]: The extracted ID if successful, None otherwise
    """
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"zdf.de", "www.zdf.de"}:
        return None

    content_id = parsed.path.strip("/")
    if content_id.endswith(".html"):
        content_id = content_id[:-5]
    return content_id or None


def find_video_urls(page_url: str, page_html: str) -> list[str]:
    """Return the playable video URLs represented by a ZDF page."""
    parsed_page = urlparse(page_url)
    clean_page_url = urlunparse(parsed_page._replace(query="", fragment=""))
    if parsed_page.path.startswith("/video/"):
        return [clean_page_url]

    # Collection pages embed canonical absolute video URLs in their RSC data.
    candidates = re.findall(
        r"https://www\.zdf\.de/video/[^\s\"\\<>]+", page_html
    )
    collection_prefix = f"/video{parsed_page.path.rstrip('/')}/"
    result = []
    seen = set()
    for candidate in candidates:
        candidate = candidate.replace(r"\u0026", "&")
        if not urlparse(candidate).path.startswith(collection_prefix):
            continue
        if candidate not in seen:
            seen.add(candidate)
            result.append(candidate)
    return result


def find_season_numbers(page_html: str) -> list[int]:
    """Extract the seasons offered by a ZDF series page."""
    return sorted(
        {int(number) for number in re.findall(r"\bStaffel\s+(\d+)\b", page_html)}
    )
