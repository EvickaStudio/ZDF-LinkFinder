import logging
import re
from typing import Any

import httpx
import requests


REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ZDF-LinkFinder/0.1)",
    "Accept-Language": "de-DE,de;q=0.9",
}


def create_async_client(max_connections: int = 8) -> httpx.AsyncClient:
    """Create the shared client used during concurrent series discovery."""
    return httpx.AsyncClient(
        headers=REQUEST_HEADERS,
        timeout=httpx.Timeout(30),
        follow_redirects=True,
        limits=httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_connections,
        ),
    )


def fetch_page(url: str) -> str | None:
    """Fetch a ZDF web page."""
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as error:
        logging.error("Failed to fetch ZDF page: %s", error)
        return None


async def fetch_page_async(url: str, client: httpx.AsyncClient) -> str | None:
    """Fetch a ZDF page through a shared asynchronous client."""
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as error:
        logging.error("Failed to fetch ZDF page: %s", error)
        return None


def extract_api_token(page_html: str) -> str | None:
    """Extract the video API token from old and current ZDF pages."""
    patterns = (
        # Current Next.js payload. Quotes are escaped inside the RSC stream.
        r'\\"videoToken\\":\{\\"apiToken\\":\\"([^"\\]+)',
        # The same object when it appears as ordinary JSON.
        r'"videoToken"\s*:\s*\{\s*"apiToken"\s*:\s*"([^"]+)',
        # Legacy ZDF pages.
        r'window\.zdfsite\.player\.apiToken\s*=\s*"([^"]+)"',
    )

    for pattern in patterns:
        if match := re.search(pattern, page_html):
            logging.info("Successfully fetched API token.")
            return match[1]

    logging.error("The ZDF page did not contain a video API token.")
    return None


def fetch_api_token(url: str) -> str | None:
    """
    Fetches API token.

    Parameters:
    url (str): The URL to fetch the API token from

    Returns:
    str | None: The API token if successful, None otherwise
    """
    page_html = fetch_page(url)
    return extract_api_token(page_html) if page_html else None


def fetch_json(url: str, headers: dict[str, str]) -> dict[str, Any] | None:
    """
    Fetches JSON data.

    Parameters:
    url (str): The URL to fetch JSON data from
    headers (Dict[str, str]): HTTP headers for the request

    Returns:
    dict | None: The fetched JSON data if successful, None otherwise
    """
    try:
        response = requests.get(
            url, headers={**REQUEST_HEADERS, **headers}, timeout=30
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        logging.error("Failed to fetch JSON from %s: %s", url, error)
        return None


async def fetch_json_async(
    url: str, headers: dict[str, str], client: httpx.AsyncClient
) -> dict[str, Any] | None:
    """Fetch JSON through a shared asynchronous client."""
    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as error:
        logging.error("Failed to fetch JSON from %s: %s", url, error)
        return None
