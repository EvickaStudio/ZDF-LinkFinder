import logging
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time

import imageio_ffmpeg
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
        self.success = False

    def run(self):
        headers = {"Range": f"bytes={self.start_byte}-{self.end_byte}"}
        retries = 0
        chunk_size = 8192  # Initial chunk size
        with requests.Session() as session:
            while retries < self.max_retries:
                bytes_downloaded = 0
                try:
                    response = session.get(
                        self.url, headers=headers, stream=True, timeout=(10, 60)
                    )
                    with response:
                        response.raise_for_status()
                        if response.status_code != 206:
                            raise requests.RequestException(
                                "The server did not honor the requested byte range."
                            )
                        start_time = time.time()
                        expected_size = self.end_byte - self.start_byte + 1
                        with open(self.filename, "r+b") as file:
                            file.seek(self.start_byte)
                            for chunk in response.iter_content(chunk_size=chunk_size):
                                if not chunk:
                                    continue
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
                    if bytes_downloaded != expected_size:
                        raise requests.RequestException(
                            f"Expected {expected_size} bytes, received {bytes_downloaded}."
                        )
                    self.success = True
                    break
                except (requests.RequestException, ConnectionError, OSError) as error:
                    if bytes_downloaded:
                        self.progress_queue.put(-bytes_downloaded)
                    retries += 1
                    logging.warning(
                        "Retry %d/%d: Failed to download chunk %d-%d. Error: %s",
                        retries,
                        self.max_retries,
                        self.start_byte,
                        self.end_byte,
                        error,
                    )


def download_hls(url: str, name: str) -> bool:
    """Download one HLS rendition and remux it to MP4 without re-encoding."""
    output_directory = os.path.dirname(os.path.abspath(name))
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output_directory,
            prefix=f".{os.path.basename(name)}.",
            suffix=".part.mp4",
            delete=False,
        ) as file:
            temporary_name = file.name

        logging.info("Downloading adaptive stream with FFmpeg.")
        subprocess.run(
            [
                imageio_ffmpeg.get_ffmpeg_exe(),
                "-hide_banner",
                "-loglevel",
                "error",
                "-stats",
                "-y",
                "-i",
                url,
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                temporary_name,
            ],
            check=True,
        )
        os.replace(temporary_name, name)
        logging.info("Downloaded %s", name)
        return True
    except (OSError, subprocess.CalledProcessError) as error:
        logging.error("Failed to download adaptive stream. Error: %s", error)
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)
        return False


def download(url: str, name: str, num_threads: int = 1) -> bool:
    """
    A utility module for downloading files from a given URL using multiple threads.

    Args:
        url (str): The URL of the file to be downloaded.
        name (str): The name of the file to be saved.
        num_threads (int, optional): The number of threads to use for downloading. Defaults to 1.

    Returns:
        bool: True if the file is downloaded successfully, otherwise False.

    Raises:
        requests.RequestException: If there is an error in the download request.

    Examples:
        # Download a file using a single thread
        download("https://example.com/file.txt", "file.txt")

        # Download a file using multiple threads
        download("https://example.com/file.txt", "file.txt", num_threads=4)
    """

    if ".m3u8" in url.lower():
        return download_hls(url, name)

    temporary_name = None
    try:
        response = requests.head(url, allow_redirects=True, timeout=30)
        response.raise_for_status()
        total_size = int(response.headers.get("Content-Length", 0))
        if total_size == 0:
            logging.error("Content-Length not found.")
            return False

        if response.headers.get("Accept-Ranges", "").lower() != "bytes":
            logging.error("The server does not support ranged downloads.")
            return False

        num_threads = max(1, min(num_threads, total_size))
        chunk_size = total_size // num_threads
        output_directory = os.path.dirname(os.path.abspath(name))
        with tempfile.NamedTemporaryFile(
            dir=output_directory,
            prefix=f".{os.path.basename(name)}.",
            suffix=".part",
            delete=False,
        ) as file:
            temporary_name = file.name
            file.truncate(total_size)

        progress_queue = queue.Queue()
        lock = threading.Lock()
        threads = [
            DownloadThread(
                url,
                i * chunk_size,
                (i + 1) * chunk_size - 1 if i < num_threads - 1 else total_size - 1,
                temporary_name,
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
        if not all(thread.success for thread in threads):
            logging.error("One or more download chunks failed.")
            os.unlink(temporary_name)
            return False

        os.replace(temporary_name, name)
        logging.info("Downloaded %s", name)
        return True

    except (requests.RequestException, OSError, ValueError) as error:
        logging.error("Failed to download %s. Error: %s", url, error)
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)
        return False
