import requests
import logging
import sys
from typing import Optional


def download(url: str, name: str) -> Optional[bool]:
    """
    Downloads a file from a given URL and saves it under a given name.
    Tracks the download progress.

    Parameters:
    url (str): URL of the file to be downloaded
    name (str): Name of the saved file

    Returns:
    Optional[bool]: True if successful, None otherwise
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise HTTPError for bad responses

        # Determine the total size of the file
        total_size = int(response.headers.get("content-length", 0))

        # Initialize variables for tracking download progress
        downloaded_size = 0
        chunk_size = 8192

        with open(name, "wb") as file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    downloaded_size += len(chunk)
                    file.write(chunk)

                    # Log download progress
                    percent_complete = (downloaded_size / total_size) * 100
                    sys.stdout.write(f"\rProgress: {percent_complete:.2f}%")
                    sys.stdout.flush()

        print()
        logging.info(f"Downloaded {name}")
        return True

    except requests.RequestException as e:
        logging.error(f"Failed to download {url}. Error: {e}")
        return None
