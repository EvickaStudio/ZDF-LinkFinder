import logging
import queue
import sys
import threading
import time
from typing import Optional

import requests


class DownloadThread(threading.Thread):
    def __init__(
        self, url, start_byte, end_byte, filename, progress_queue, lock, max_retries=3
    ):
        super().__init__()
        self.url = url
        self.start_byte = start_byte
        self.end_byte = end_byte
        self.filename = filename
        self.progress_queue = progress_queue
        self.lock = lock
        self.max_retries = max_retries

    def run(self):
        headers = {"Range": f"bytes={self.start_byte}-{self.end_byte}"}
        retries = 0
        chunk_size = 8192  # Initial chunk size
        with requests.Session() as session:
            while retries < self.max_retries:
                try:
                    response = session.get(
                        self.url, headers=headers, stream=True, timeout=5
                    )
                    start_time = time.time()
                    bytes_downloaded = 0
                    with open(self.filename, "wb") as file:
                        file.seek(self.start_byte)
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            elapsed_time = time.time() - start_time
                            download_speed = bytes_downloaded / (
                                elapsed_time + 1e-9
                            )  # bytes per second
                            optimal_chunk_size = int(
                                download_speed * 0.1
                            )  # Aim to download a chunk in 0.1 seconds
                            chunk_size = max(
                                8192, min(optimal_chunk_size, 8192 * 16)
                            )  # Clamp between 8 KB and 128 KB

                            with self.lock:
                                file.write(chunk)
                            bytes_downloaded += len(chunk)
                            self.progress_queue.put(len(chunk))
                    break
                except (requests.exceptions.RequestException, ConnectionError) as e:
                    retries += 1
                    logging.warning(
                        f"Retry {retries}/{self.max_retries}: Failed to download chunk {self.start_byte}-{self.end_byte}. Error: {e}"
                    )


def download(url: str, name: str, num_threads: int = 1) -> Optional[bool]:
    """
    A utility module for downloading files from a given URL using multiple threads.

    Args:
        url (str): The URL of the file to be downloaded.
        name (str): The name of the file to be saved.
        num_threads (int, optional): The number of threads to use for downloading. Defaults to 1.

    Returns:
        bool or None: Returns True if the file is downloaded successfully, None if there is an error.

    Raises:
        requests.RequestException: If there is an error in the download request.

    Examples:
        # Download a file using a single thread
        download("https://example.com/file.txt", "file.txt")

        # Download a file using multiple threads
        download("https://example.com/file.txt", "file.txt", num_threads=4)
    """

    try:
        response = requests.head(url)
        total_size = int(response.headers.get("Content-Length", 0))
        if total_size == 0:
            logging.error("Content-Length not found.")
            return None

        chunk_size = total_size // num_threads
        with open(name, "wb") as file:
            file.write(b"\0" * total_size)

        progress_queue = queue.Queue()
        lock = threading.Lock()
        threads = [
            DownloadThread(
                url,
                i * chunk_size,
                (i + 1) * chunk_size - 1 if i < num_threads - 1 else total_size - 1,
                name,
                progress_queue,
                lock,
            )
            for i in range(num_threads)
        ]
        total_size_mb = total_size / (1024 * 1024)
        start_time = time.time()
        [thread.start() for thread in threads]
        downloaded_size = 0
        bar_length = 50
        while (
            any(thread.is_alive() for thread in threads) or not progress_queue.empty()
        ):
            while not progress_queue.empty():
                downloaded_size += progress_queue.get()
            time.sleep(0.5)  # Update UI less frequently
            elapsed_time = time.time() - start_time
            speed_kb = downloaded_size / (elapsed_time + 1e-9) / 1024
            speed_mb = speed_kb / 1024
            speed, unit = (speed_mb, "MB/s") if speed_mb > 1 else (speed_kb, "KB/s")
            downloaded_size_mb = downloaded_size / (1024 * 1024)
            percent_complete = (downloaded_size / total_size) * 100
            progress = int(bar_length * downloaded_size // total_size)
            progress_bar = f"[{'▇' * progress}{'-' * (bar_length - progress)}]"
            sys.stdout.write(
                f"\r{percent_complete:.2f}% - {progress_bar} {downloaded_size_mb:.2f}/{total_size_mb:.2f} MB - {speed:.2f} {unit}"
            )
            sys.stdout.flush()

        [thread.join() for thread in threads]
        print()
        logging.info(f"Downloaded {name}")
        return True

    except requests.RequestException as e:
        logging.error(f"Failed to download {url}. Error: {e}")
        return None
