import logging
from urllib.parse import urlparse


def validate_url(url: str) -> bool:
    """
    Validates the URL using a regular expression.

    Parameters:
    url (str): The URL to be validated

    Returns:
    bool: True if the URL is valid, False otherwise
    """
    parsed = urlparse(url)
    is_valid = (
        parsed.scheme == "https"
        and parsed.hostname in {"zdf.de", "www.zdf.de"}
        and bool(parsed.path.strip("/"))
    )

    if is_valid:
        logging.info("Valid URL!")
    else:
        logging.warning(f"Invalid URL: {url}")

    return is_valid
