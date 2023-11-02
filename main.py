import logging
from typing import Dict, Union, Tuple
from api.fetcher import fetch_api_token
from utils.formatter import format_duration
from utils.extractor import (
    extract_additional_info,
    list_quality_options,
    fetch_metadata_and_stream_data,
)
from utils.downloader import download
from utils.validate import validate_url

logging.basicConfig(level=logging.INFO)


def extract_data(
    metadata: Dict[str, Union[str, int]], stream_data: Dict[str, Union[str, int]]
) -> Tuple[str, Dict[str, str]]:
    """
    Extracts and formats the data.
    """
    additional_info = extract_additional_info(metadata)
    quality_options = list_quality_options(stream_data)

    # Correctly handle duration formatting
    duration_milliseconds = stream_data["attributes"]["duration"]["value"]
    formatted_duration = format_duration(duration_milliseconds)

    return additional_info, quality_options, formatted_duration


def main(url: str):
    if not validate_url(url):
        logging.error("Invalid URL.")
        return

    api_token = fetch_api_token(url)
    if api_token is None:
        logging.error("Failed to fetch API token.")
        return

    headers = {"Api-Auth": f"Bearer {api_token}"}

    metadata, stream_data = fetch_metadata_and_stream_data(url, headers)

    title = metadata.get("title", "Unknown Title")
    logging.info(f"Title: {title}")

    additional_info, quality_options, formatted_duration = extract_data(
        metadata, stream_data
    )
    logging.info(f"Additional Info: {additional_info}")
    logging.info(f"Quality Options: {quality_options}")
    logging.info(f"Formatted Duration: {formatted_duration}")

    # Further processing and downloading can be done here
    # For example: download(quality_options["high"], quality_options["high"].split("/")[-1]) to download the highest quality video with original filename
    download(quality_options["high"], quality_options["high"].split("/")[-1], num_threads=4)


if __name__ == "__main__":
    url = input("Enter URL: ")
    main(url)
