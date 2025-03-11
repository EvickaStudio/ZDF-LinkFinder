import argparse
import logging
import os
from typing import Dict, Tuple, Union

from api.fetcher import fetch_api_token
from utils.downloader import download
from utils.extractor import (
    extract_additional_info,
    fetch_metadata_and_stream_data,
    list_quality_options,
)
from utils.formatter import format_duration
from utils.validate import validate_url


def setup_logging(verbose: bool = False):
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def extract_data(
    metadata: Dict[str, Union[str, int]], stream_data: Dict[str, Union[str, int]]
) -> Tuple[str, Dict[str, str], str]:
    """
    Extracts and formats the data.
    """
    additional_info = extract_additional_info(metadata)
    quality_options = list_quality_options(stream_data)

    # Correctly handle duration formatting
    duration_milliseconds = stream_data["attributes"]["duration"]["value"]
    formatted_duration = format_duration(duration_milliseconds)

    return additional_info, quality_options, formatted_duration


def main(args):
    """Main function for the ZDF Link Finder program."""
    # Set up logging based on verbosity flag
    setup_logging(args.verbose)

    url = args.url
    if not validate_url(url):
        logging.error("Invalid URL.")
        return False

    logging.info(f"Processing URL: {url}")
    api_token = fetch_api_token(url)
    if api_token is None:
        logging.error("Failed to fetch API token.")
        return False

    headers = {"Api-Auth": f"Bearer {api_token}"}

    metadata, stream_data = fetch_metadata_and_stream_data(url, headers)

    title = metadata.get("title", "Unknown Title")
    logging.info(f"Title: {title}")

    additional_info, quality_options, formatted_duration = extract_data(
        metadata, stream_data
    )

    if args.verbose:
        logging.info(f"Additional Info: {additional_info}")
        logging.info(f"Available Quality Options: {list(quality_options.keys())}")
        logging.info(f"Formatted Duration: {formatted_duration}")

    # Determine quality
    if args.list_qualities:
        print("\nAvailable Quality Options:")
        for quality_name, url in quality_options.items():
            print(f"  {quality_name}: {url}")
        return True

    quality = args.quality

    # Separate the available qualities by format type
    direct_download_qualities = {}
    streaming_qualities = {}

    for quality_name, url in quality_options.items():
        if ".m3u8" in url:
            streaming_qualities[quality_name] = url
        else:
            direct_download_qualities[quality_name] = url

    if args.best:
        # Select the best direct download quality automatically
        if direct_download_qualities:
            # Priority list for best quality selection
            for preferred in ["hd", "veryhigh", "high", "med", "low"]:
                if preferred in direct_download_qualities:
                    quality = preferred
                    logging.info(
                        f"Selected best available direct download quality: '{quality}'"
                    )
                    break
            else:
                # If none of the preferred qualities found, take the first available
                quality = list(direct_download_qualities.keys())[0]
                logging.info(f"Selected available quality: '{quality}'")
        else:
            logging.error("No direct download qualities available.")
            return False
    else:
        # User specified quality
        if quality not in quality_options:
            logging.warning(
                f"Requested quality '{quality}' not available. Available options: {list(quality_options.keys())}"
            )
            # Find the best available quality as fallback
            for preferred in ["veryhigh", "high", "med"]:
                if preferred in direct_download_qualities:
                    quality = preferred
                    logging.info(f"Using '{quality}' quality instead.")
                    break
            else:
                if direct_download_qualities:
                    quality = list(direct_download_qualities.keys())[0]
                else:
                    logging.error("No direct download qualities available.")
                    return False
                logging.info(f"Using '{quality}' quality instead.")

    video_url = quality_options[quality]

    # Check if selected quality is a streaming format
    if ".m3u8" in video_url:
        logging.error(
            f"The selected quality '{quality}' is a streaming format (m3u8) which is not supported for direct download."
        )
        logging.info(
            f"Available direct download qualities: {list(direct_download_qualities.keys()) if direct_download_qualities else 'None'}"
        )
        logging.info(
            "Please select a different quality or use '--best' to automatically select the best direct download quality."
        )
        return False

    # Determine output filename
    if args.output:
        output_filename = args.output
    else:
        # Use the title and quality for filename if not specified
        default_filename = f"{title.replace(' ', '_')}_{quality}.mp4"
        # Clean up filename
        default_filename = "".join(
            c for c in default_filename if c.isalnum() or c in ["_", "-", "."]
        )
        output_filename = default_filename

    # Avoid overwriting existing files unless forced
    if os.path.exists(output_filename) and not args.force:
        logging.warning(
            f"File '{output_filename}' already exists. Use --force to overwrite."
        )
        i = 1
        base, ext = os.path.splitext(output_filename)
        while os.path.exists(f"{base}_{i}{ext}"):
            i += 1
        output_filename = f"{base}_{i}{ext}"
        logging.info(f"Saving as '{output_filename}' instead.")

    logging.info(f"Downloading '{title}' in {quality} quality to '{output_filename}'")
    success = download(video_url, output_filename, num_threads=args.threads)

    if success:
        logging.info(f"Successfully downloaded to {output_filename}")
        return True
    else:
        logging.error("Download failed")
        return False


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="ZDF-LinkFinder - Download videos from ZDF Mediathek",
        epilog="Example: python main.py https://www.zdf.de/serien/example-show/episode-1-100.html --quality high",
    )

    parser.add_argument("url", nargs="?", help="URL of the ZDF video to download")

    parser.add_argument(
        "-q",
        "--quality",
        default="veryhigh",
        help="Quality to download (default: veryhigh)",
    )

    parser.add_argument(
        "-o", "--output", help="Output filename (default: [title]_[quality].mp4)"
    )

    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=4,
        help="Number of download threads (default: 4)",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force overwrite if output file exists",
    )

    parser.add_argument(
        "-l",
        "--list-qualities",
        action="store_true",
        help="List available quality options without downloading",
    )

    parser.add_argument(
        "-b",
        "--best",
        action="store_true",
        help="Automatically select the best available direct download quality",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    # If URL wasn't provided as an argument, prompt for it
    if not args.url:
        args.url = input("Enter URL: ")

    success = main(args)
    exit(0 if success else 1)
