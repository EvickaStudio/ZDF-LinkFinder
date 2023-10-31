import requests
import re
import logging
from typing import Union, Dict


def fetch_api_token(url: str) -> Union[str, None]:
    """
    Fetches API token.

    Parameters:
    url (str): The URL to fetch the API token from

    Returns:
    Union[str, None]: The API token if successful, None otherwise
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        # Fix the regex pattern for extracting the API token
        api_token = re.search(
            r'window\.zdfsite\.player\.apiToken = "([\d\w]+)";', response.text
        )[1]
        logging.info(f"Successfully fetched API token: {api_token}")
        return api_token
    except (requests.RequestException, TypeError, IndexError) as e:
        logging.error(f"Failed to fetch API token. Error: {e}")
        return None


def fetch_json(
    url: str, headers: Dict[str, str]
) -> Union[Dict[str, Union[str, int]], None]:
    """
    Fetches JSON data.

    Parameters:
    url (str): The URL to fetch JSON data from
    headers (Dict[str, str]): HTTP headers for the request

    Returns:
    Union[Dict[str, Union[str, int]], None]: The fetched JSON data if successful, None otherwise
    """
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as e:
        logging.error(f"Failed to fetch JSON. Error: {e}")
        return None
