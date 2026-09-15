import argparse
import asyncio
import logging
import os
import re
import sys
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from api.fetcher import (
    create_async_client,
    extract_api_token,
    fetch_page,
    fetch_page_async,
)
from utils.downloader import download
from utils.extractor import (
    add_hls_quality_options,
    extract_additional_info,
    extract_episode_info,
    fetch_metadata_async,
    fetch_metadata_and_stream_data,
    list_quality_options,
)
from utils.formatter import format_duration
from utils.url_utils import find_season_numbers, find_video_urls
from utils.validate import validate_url


@dataclass
class EpisodeEntry:
    url: str
    metadata: dict[str, Any]
    season: int
    episode: int
    title: str


def setup_logging(verbose: bool = False):
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def extract_data(
    metadata: dict[str, Any], stream_data: dict[str, Any]
) -> tuple[str | None, dict[str, str], str]:
    """
    Extracts and formats the data.
    """
    additional_info = extract_additional_info(metadata)
    quality_options = add_hls_quality_options(list_quality_options(stream_data))

    # Correctly handle duration formatting
    duration_milliseconds = stream_data["attributes"]["duration"]["value"]
    formatted_duration = format_duration(duration_milliseconds)

    return additional_info, quality_options, formatted_duration


def _file_extension(video_url: str) -> str:
    if ".m3u8" in video_url.lower():
        return ".mp4"
    extension = os.path.splitext(urlparse(video_url).path)[1].lower()
    return extension if extension in {".mp4", ".webm"} else ".mp4"


def _best_quality_name(quality_options: dict[str, str]) -> str:
    resolution_options = []
    for name in quality_options:
        if match := re.fullmatch(r"(\d+)p(?:(\d+))?", name):
            resolution_options.append((int(match[1]), int(match[2] or 0), name))
    if resolution_options:
        return max(resolution_options)[2]

    for preferred in ["hd", "veryhigh", "high", "med", "low"]:
        if preferred in quality_options:
            return preferred
    return next(iter(quality_options))


def _choose_quality(quality_options: dict[str, str], args) -> str:
    best_quality = _best_quality_name(quality_options)
    if args.best or args.quality == "best":
        return best_quality
    if args.quality:
        return args.quality.lower()
    if not sys.stdin.isatty():
        return best_quality

    names = list(quality_options)
    print("\nChoose download quality:")
    print(f"  1. best available for each video ({best_quality} for this video)")
    for index, name in enumerate(names, start=2):
        print(f"  {index}. {name}")
    try:
        selection = input("Selection [1]: ").strip().lower()
    except EOFError:
        selection = ""
    if not selection or selection in {"1", "best"}:
        args.best = True
        return best_quality
    if selection.isdigit() and 2 <= int(selection) <= len(names) + 1:
        selected = names[int(selection) - 2]
    else:
        selected = selection

    # Reuse an explicitly chosen fixed quality for every selected episode.
    args.quality = selected
    return selected


def _parse_number_selection(value: str, available: list[int]) -> list[int]:
    """Parse selections such as 'all', '1,3', or '1-4'."""
    normalized = value.strip().lower().replace(" ", "")
    if normalized in {"all", "*"}:
        return list(available)
    if not normalized:
        raise ValueError("The selection cannot be empty.")

    selected = set()
    for part in normalized.split(","):
        if not part:
            raise ValueError("Invalid empty selection item.")
        if "-" in part:
            bounds = part.split("-")
            if len(bounds) != 2 or not all(bound.isdigit() for bound in bounds):
                raise ValueError(f"Invalid range: {part}")
            start, end = map(int, bounds)
            if start > end:
                raise ValueError(f"Range must be ascending: {part}")
            selected.update(range(start, end + 1))
        elif part.isdigit():
            selected.add(int(part))
        else:
            raise ValueError(f"Invalid selection item: {part}")

    if invalid := sorted(selected.difference(available)):
        raise ValueError(f"Unavailable number(s): {', '.join(map(str, invalid))}")
    return [number for number in available if number in selected]


def _choose_numbers(
    label: str,
    available: list[int],
    default: str,
    configured: str | None,
) -> list[int]:
    if configured:
        return _parse_number_selection(configured, available)
    if not sys.stdin.isatty():
        return _parse_number_selection(default, available)

    while True:
        try:
            selection = input(
                f"Select {label} (all, 1, 1-3, 1,3) [{default}]: "
            ).strip()
        except EOFError:
            selection = ""
        try:
            return _parse_number_selection(selection or default, available)
        except ValueError as error:
            print(f"Invalid selection: {error}")


def _url_for_season(url: str, season: int) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query["staffel"] = [str(season)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


async def _discover_series_episodes(
    url: str,
    seasons: list[int],
    headers: dict[str, str],
) -> list[EpisodeEntry]:
    concurrency = asyncio.Semaphore(8)
    async with create_async_client(max_connections=8) as client:
        async def load_season(season: int) -> tuple[int, str, str | None]:
            season_url = _url_for_season(url, season)
            async with concurrency:
                page_html = await fetch_page_async(season_url, client)
            return season, season_url, page_html

        season_pages = await asyncio.gather(
            *(load_season(season) for season in seasons)
        )
        candidate_urls = []
        seen_urls = set()
        for season, season_url, page_html in season_pages:
            if page_html is None:
                logging.warning("Could not load season %d.", season)
                continue
            for video_url in find_video_urls(season_url, page_html):
                if video_url not in seen_urls:
                    seen_urls.add(video_url)
                    candidate_urls.append(video_url)

        async def load_metadata(
            video_url: str,
        ) -> tuple[str, dict[str, Any] | None]:
            try:
                async with concurrency:
                    metadata = await fetch_metadata_async(video_url, headers, client)
                return video_url, metadata
            except (ValueError, RuntimeError) as error:
                logging.debug("Skipping %s: %s", video_url, error)
                return video_url, None

        metadata_results = await asyncio.gather(
            *(load_metadata(video_url) for video_url in candidate_urls)
        )

    entries = {}
    for video_url, metadata in metadata_results:
        if metadata is not None:
            episode_info = extract_episode_info(metadata)
            if not episode_info or episode_info[0] not in seasons:
                continue
            season_number, episode_number = episode_info
            entries[video_url] = EpisodeEntry(
                url=video_url,
                metadata=metadata,
                season=season_number,
                episode=episode_number,
                title=str(metadata.get("title", "Unknown Title")),
            )

    return sorted(
        entries.values(), key=lambda entry: (entry.season, entry.episode, entry.title)
    )


def _choose_series_episodes(
    entries: list[EpisodeEntry], configured: str | None
) -> list[EpisodeEntry]:
    print("\nAvailable episodes:")
    for selection_id, entry in enumerate(entries, start=1):
        print(
            f"  {selection_id}. S{entry.season:02d}E{entry.episode:02d} - {entry.title}"
        )

    available_ids = list(range(1, len(entries) + 1))
    selected_ids = _choose_numbers(
        "episode IDs", available_ids, "all", configured
    )
    return [entries[selection_id - 1] for selection_id in selected_ids]


def process_video(
    url: str,
    headers: dict[str, str],
    args,
    *,
    metadata: dict[str, Any] | None = None,
    filename_prefix: str = "",
) -> bool:
    """Resolve and optionally download one playable ZDF video."""
    try:
        metadata, stream_data = fetch_metadata_and_stream_data(
            url, headers, metadata=metadata
        )
        additional_info, quality_options, formatted_duration = extract_data(
            metadata, stream_data
        )
    except (KeyError, TypeError, ValueError, RuntimeError) as error:
        logging.error("Failed to resolve %s: %s", url, error)
        return False

    title = metadata.get("title", "Unknown Title")
    logging.info("Title: %s", title)

    if args.verbose:
        logging.info("Additional Info: %s", additional_info)
        logging.info("Available Quality Options: %s", list(quality_options))
        logging.info("Formatted Duration: %s", formatted_duration)

    if not quality_options:
        logging.error("No downloadable qualities were found for '%s'.", title)
        return False

    if args.list_qualities:
        print(f"\nAvailable Quality Options for '{title}':")
        for quality_name, quality_url in quality_options.items():
            print(f"  {quality_name}: {quality_url}")
        return True

    quality = _choose_quality(quality_options, args)
    if quality not in quality_options:
        fallback = _best_quality_name(quality_options)
        logging.warning(
            "Requested quality '%s' is unavailable. Using '%s' instead. Available options: %s",
            quality,
            fallback,
            list(quality_options),
        )
        quality = fallback

    video_url = quality_options[quality]

    # Determine output filename
    if args.output:
        output_filename = args.output
    else:
        extension = _file_extension(video_url)
        default_filename = (
            f"{filename_prefix}{title.replace(' ', '_')}_{quality}{extension}"
        )
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

    logging.info(
        "Downloading '%s' in %s quality to '%s'", title, quality, output_filename
    )
    if success := download(  # noqa: F841
        video_url, output_filename, num_threads=args.threads
    ):
        logging.info(f"Successfully downloaded to {output_filename}")
        return True
    else:
        logging.error("Download failed")
        return False


def main(args):
    """Main function for the ZDF Link Finder program."""
    setup_logging(args.verbose)

    url = args.url
    if not validate_url(url):
        logging.error("Invalid URL.")
        return False

    logging.info("Processing URL: %s", url)
    page_html = fetch_page(url)
    if page_html is None:
        return False

    api_token = extract_api_token(page_html)
    if api_token is None:
        return False

    headers = {"Api-Auth": f"Bearer {api_token}"}
    parsed_url = urlparse(url)
    seasons = (
        find_season_numbers(page_html)
        if parsed_url.path.startswith("/serien/")
        else []
    )
    if seasons:
        query_season = parse_qs(parsed_url.query).get("staffel", [None])[0]
        default_season = (
            query_season
            if query_season and query_season.isdigit() and int(query_season) in seasons
            else str(max(seasons))
        )
        print(f"\nAvailable seasons: {', '.join(map(str, seasons))}")
        try:
            selected_seasons = _choose_numbers(
                "seasons", seasons, default_season, args.seasons
            )
        except ValueError as error:
            logging.error("Invalid season selection: %s", error)
            return False

        logging.info(
            "Loading season(s): %s", ", ".join(map(str, selected_seasons))
        )
        entries = asyncio.run(
            _discover_series_episodes(url, selected_seasons, headers)
        )
        if not entries:
            logging.error("No available episodes were found in the selected seasons.")
            return False
        try:
            selected_entries = _choose_series_episodes(entries, args.episodes)
        except ValueError as error:
            logging.error("Invalid episode selection: %s", error)
            return False

        if len(selected_entries) > 1 and args.output:
            logging.error("--output can only be used when one episode is selected.")
            return False
        logging.info("Selected %d episode(s).", len(selected_entries))
        results = [
            process_video(
                entry.url,
                headers,
                args,
                metadata=entry.metadata,
                filename_prefix=f"S{entry.season:02d}E{entry.episode:02d}_",
            )
            for entry in selected_entries
        ]
        return all(results)

    video_urls = find_video_urls(url, page_html)
    if not video_urls:
        logging.error("The ZDF page does not contain an available video.")
        return False

    if len(video_urls) > 1:
        logging.info("Found %d episodes on the series page.", len(video_urls))
        if args.output:
            logging.error("--output can only be used with a single video URL.")
            return False

    results = [
        process_video(video_url, headers, args)
        for video_url in video_urls
    ]
    return all(results)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="ZDF-LinkFinder - Download videos from ZDF Mediathek",
        epilog="Example: uv run main.py https://www.zdf.de/filme/bis-es-blutet-movie-100 --quality high",
    )

    parser.add_argument("url", nargs="?", help="URL of the ZDF video to download")

    parser.add_argument(
        "-q",
        "--quality",
        help="Quality to download, for example 1080p50 or veryhigh",
    )

    parser.add_argument(
        "-o", "--output", help="Output filename (default: [title]_[quality].[format])"
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
        help="Automatically select the highest available quality without prompting",
    )

    parser.add_argument(
        "--seasons",
        metavar="SELECTION",
        help="Series seasons to use: all, 1, 1-3, or 1,3",
    )

    parser.add_argument(
        "--episodes",
        metavar="SELECTION",
        help="Episode IDs to use after season filtering: all, 1, 1-3, or 1,3",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    # If URL wasn't provided as an argument, prompt for it
    if not args.url:
        args.url = input("Enter URL: ")

    success = main(args)
    exit(0 if success else 1)
