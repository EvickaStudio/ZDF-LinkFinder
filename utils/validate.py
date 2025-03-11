import logging
import re


def validate_url(url: str) -> bool:
    """
    Validates the URL using a regular expression.

    Parameters:
    url (str): The URL to be validated

    Returns:
    bool: True if the URL is valid, False otherwise
    """
    # Fix the regex pattern
    pattern = r"https://(?:www\.)?zdf\.de/[\w/-]+\.html"
    is_valid = re.match(pattern, url) is not None

    if is_valid:
        logging.info("Valid URL!")
    else:
        logging.warning(f"Invalid URL: {url}")

    return is_valid
