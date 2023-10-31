import requests
import logging
import sys
import time
from typing import Optional

def download(url: str, name: str) -> Optional[bool]:
    """
    Downloads a file from a given URL and saves it under a given name.
    Tracks the download progress, speed, amount of MB downloaded, and includes a progress bar.

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
        total_size_mb = total_size / (1024 * 1024)

        # Initialize variables for tracking download progress and speed
        downloaded_size = 0
        chunk_size = 8192
        start_time = time.time()

        with open(name, "wb") as file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    downloaded_size += len(chunk)
                    file.write(chunk)

                    # Calculate download progress and speed
                    elapsed_time = time.time() - start_time
                    speed_kb = downloaded_size / (elapsed_time + 1e-9) / 1024  # in KB/s (added a small constant to avoid ZeroDivisionError)
                    speed_mb = speed_kb / 1024  # in MB/s
                    speed, unit = (speed_mb, "MB/s") if speed_mb > 1 else (speed_kb, "KB/s")
                    
                    downloaded_size_mb = downloaded_size / (1024 * 1024)
                    percent_complete = (downloaded_size / total_size) * 100

                    # Generate progress bar
                    bar_length = 50
                    progress = int(bar_length * downloaded_size // total_size)
                    progress_bar = f"[{'#' * progress}{'.' * (bar_length - progress)}]"
                    
                    sys.stdout.write(f"\r{percent_complete:.2f}% - {progress_bar} {downloaded_size_mb:.2f}/{total_size_mb:.2f} MB - {speed:.2f} {unit}")
                    sys.stdout.flush()

        print()
        logging.info(f"Downloaded {name}")
        return True

    except requests.RequestException as e:
        logging.error(f"Failed to download {url}. Error: {e}")
        return None