import re
from typing import Any
from urllib.parse import urljoin

import httpx

from api.fetcher import fetch_json, fetch_json_async, fetch_page
from utils.url_utils import get_id_from_url


API_BASE_URL = "https://api.zdf.de"
MOVED_PERMANENTLY_PROFILE = "http://zdf.de/rels/moved-permanently"


def extract_additional_info(metadata: dict[str, Any]) -> str | None:
    """
    Extracts additional information.
    """
    return metadata.get("leadParagraph")


def list_quality_options(stream_data: dict[str, Any]) -> dict[str, str]:
    """
    Lists available quality options.
    """
    qualities = {}
    scores = {}
    for item in stream_data["priorityList"]:
        for form in item["formitaeten"]:
            for quality in form["qualities"]:
                quality_name = quality["quality"]
                tracks = quality.get("audio", {}).get("tracks", [])
                main_track = next(
                    (track for track in tracks if track.get("class") == "main"),
                    tracks[0] if tracks else None,
                )
                if not main_track:
                    continue

                mime_type = form.get("mimeType", "")
                score = (
                    not form.get("isAdaptive", False),
                    mime_type == "video/mp4",
                    mime_type == "video/webm",
                )
                if quality_name not in scores or score > scores[quality_name]:
                    qualities[quality_name] = main_track["uri"]
                    scores[quality_name] = score
    return qualities


def add_hls_quality_options(qualities: dict[str, str]) -> dict[str, str]:
    """Expand an HLS master playlist into resolution-based quality choices."""
    master_url = qualities.get("auto") or next(
        (url for url in qualities.values() if ".m3u8" in url), None
    )
    if not master_url:
        return qualities

    playlist = fetch_page(master_url)
    if not playlist:
        return qualities

    variants: dict[str, tuple[int, str]] = {}
    lines = [line.strip() for line in playlist.splitlines()]
    for index, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF:"):
            continue

        resolution = re.search(r"RESOLUTION=(\d+)x(\d+)", line)
        if not resolution:
            continue
        frame_rate = re.search(r"FRAME-RATE=([\d.]+)", line)
        bandwidth = re.search(r"BANDWIDTH=(\d+)", line)
        width, height = map(int, resolution.groups())
        fps = round(float(frame_rate[1])) if frame_rate else None
        label = f"{height}p{fps}" if fps and fps > 30 else f"{height}p"

        variant_url = next(
            (
                lines[next_index]
                for next_index in range(index + 1, len(lines))
                if lines[next_index] and not lines[next_index].startswith("#")
            ),
            None,
        )
        if not variant_url:
            continue
        score = int(bandwidth[1]) if bandwidth else width * height
        if label not in variants or score > variants[label][0]:
            variants[label] = (score, urljoin(master_url, variant_url))

    if not variants:
        return qualities

    expanded = {
        label: url
        for label, (_, url) in sorted(
            variants.items(), key=lambda item: item[1][0], reverse=True
        )
    }
    expanded |= (
        (name, url) for name, url in qualities.items() if ".m3u8" not in url
    )
    return expanded


def _fetch_content_document(
    content_id: str, headers: dict[str, str]
) -> dict[str, Any]:
    url = f"{API_BASE_URL}/content/documents/zdf/{content_id}.json"
    for _ in range(5):
        document = fetch_json(url, headers)
        if document is None:
            raise RuntimeError("Could not fetch the ZDF content document.")
        if document.get("profile") != MOVED_PERMANENTLY_PROFILE:
            return document

        if location := document.get("location"):
            url = urljoin(API_BASE_URL, location)

        else:
            raise RuntimeError("ZDF returned a content redirect without a location.")
    raise RuntimeError("Too many redirects while resolving the ZDF content document.")


def fetch_metadata(url: str, headers: dict[str, str]) -> dict[str, Any]:
    """Fetch a video's content document without fetching its streams."""
    if content_id := get_id_from_url(url):
        return _fetch_content_document(content_id, headers)
    raise ValueError("Could not determine the ZDF content ID from the URL.")


async def fetch_metadata_async(
    url: str, headers: dict[str, str], client: httpx.AsyncClient
) -> dict[str, Any]:
    """Fetch a video's content document through a shared async client."""
    content_id = get_id_from_url(url)
    if not content_id:
        raise ValueError("Could not determine the ZDF content ID from the URL.")

    document_url = f"{API_BASE_URL}/content/documents/zdf/{content_id}.json"
    for _ in range(5):
        document = await fetch_json_async(document_url, headers, client)
        if document is None:
            raise RuntimeError("Could not fetch the ZDF content document.")
        if document.get("profile") != MOVED_PERMANENTLY_PROFILE:
            return document

        if location := document.get("location"):
            document_url = urljoin(API_BASE_URL, location)

        else:
            raise RuntimeError("ZDF returned a content redirect without a location.")
    raise RuntimeError("Too many redirects while resolving the ZDF content document.")


def extract_episode_info(metadata: dict[str, Any]) -> tuple[int, int] | None:
    """Return a video's season and episode numbers when ZDF provides them."""
    programme_items = metadata.get("programmeItem") or []
    programme = (
        programme_items[0].get("http://zdf.de/rels/target", {})
        if programme_items
        else {}
    )
    season = programme.get("http://zdf.de/rels/cmdm/season", {}).get(
        "seasonNumber"
    )
    episode = programme.get("episodeNumber")
    if season is None or episode is None:
        episode_info = metadata.get("episodeInfo") or {}
        season = season if season is not None else episode_info.get("seasonNumber")
        episode = episode if episode is not None else episode_info.get("episodeNumber")
    if season is None or episode is None:
        return None
    return int(season), int(episode)


def fetch_metadata_and_stream_data(
    url: str,
    headers: dict[str, str],
    metadata: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Fetches metadata and stream data.
    """
    metadata = metadata or fetch_metadata(url, headers)

    try:
        video = metadata["mainVideoContent"]["http://zdf.de/rels/target"]
        default_stream = video["streams"]["default"]
    except (KeyError, TypeError) as error:
        raise ValueError("The ZDF URL does not refer to a playable video.") from error

    if ptmd_template := default_stream.get(
        "http://zdf.de/rels/streams/ptmd-template"
    ) or video.get("http://zdf.de/rels/streams/ptmd-template"):
        stream_list_url = urljoin(
            API_BASE_URL, ptmd_template.replace("{playerId}", "ngplayer_2_4")
        )
    elif ext_id := default_stream.get("extId"):
        stream_list_url = (
            f"{API_BASE_URL}/tmd/2/ngplayer_2_4/vod/ptmd/mediathek/{ext_id}"
        )
    else:
        raise ValueError("The ZDF video does not expose a PTMD stream URL.")
    stream_data = fetch_json(stream_list_url, headers)
    if stream_data is None:
        raise RuntimeError("Could not fetch the ZDF stream metadata.")

    return metadata, stream_data
