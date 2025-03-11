from typing import Dict, Tuple, Union

from api.fetcher import fetch_json
from utils.url_utils import get_id_from_url


def extract_additional_info(metadata: Dict[str, Union[str, int]]) -> Union[str, None]:
    """
    Extracts additional information.
    """
    return metadata.get("leadParagraph")


def list_quality_options(stream_data: Dict[str, Union[str, int]]) -> Dict[str, str]:
    """
    Lists available quality options.
    """
    qualities = {}
    for item in stream_data["priorityList"]:
        for form in item["formitaeten"]:
            for quality in form["qualities"]:
                quality_name = quality["quality"]
                download_uri = quality["audio"]["tracks"][0]["uri"]
                qualities[quality_name] = download_uri
    return qualities


def fetch_metadata_and_stream_data(
    url: str, headers: Dict[str, str]
) -> Tuple[Dict[str, Union[str, int]], Dict[str, Union[str, int]]]:
    """
    Fetches metadata and stream data.
    """
    id = get_id_from_url(url)
    metadata_url = f"https://api.zdf.de/content/documents/zdf/{id}.json"
    metadata = fetch_json(metadata_url, headers)

    extId = metadata["mainVideoContent"]["http://zdf.de/rels/target"]["streams"][
        "default"
    ]["extId"]
    stream_list_url = (
        f"https://api.zdf.de/tmd/2/ngplayer_2_4/vod/ptmd/mediathek/{extId}"
    )
    stream_data = fetch_json(stream_list_url, headers)

    return metadata, stream_data
