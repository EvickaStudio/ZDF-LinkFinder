import logging
from api.fetcher import fetch_api_token, fetch_json
from utils.formatter import format_duration
from utils.extractor import extract_additional_info, list_quality_options
import re

logging.basicConfig(level=logging.INFO)

def validate_url(url: str) -> bool:
    """Validiert die URL mithilfe eines regulären Ausdrucks.
    
    Params:
        url (str): Die zu validierende URL.
        
    Returns:
        bool: True, wenn die URL gültig ist, sonst False.
    """
    # https://www.zdf.de/dokumentation/zdfinfo-doku/mythos-die-groessten-raetsel-der-geschichte--drachen-100.html
    pattern = r"https://(?:www\.)?zdf\.de/(?P<ID>[/\w-]+)\.html"
    return bool(re.match(pattern, url))

def get_id_from_url(url: str) -> str:
    """Extrahiert die ID aus der URL."""
    pattern = r"https://(?:www\.)?zdf\.de/(?P<ID>[/\w-]+)\.html"
    return re.match(pattern, url).group("ID")

def fetch_metadata_and_stream_data(url: str, headers: dict) -> tuple:
    """Holt Metadaten und Stream-Daten."""
    id = get_id_from_url(url)
    filename_url = f"https://api.zdf.de/content/documents/zdf/{id}.json"
    metadata = fetch_json(filename_url, headers)
    
    extId = metadata["mainVideoContent"]["http://zdf.de/rels/target"]["streams"]["default"]["extId"]
    stream_list_url = f"https://api.zdf.de/tmd/2/ngplayer_2_4/vod/ptmd/mediathek/{extId}"
    return metadata, fetch_json(stream_list_url, headers)


def extract_metadata(url: str, headers: dict) -> dict:
    """Extrahiert Metadaten."""
    id = get_id_from_url(url)
    filename_url = f"https://api.zdf.de/content/documents/zdf/{id}.json"
    return fetch_json(filename_url, headers)

def extract_stream_data(metadata: dict, headers: dict) -> dict:
    """Extrahiert Stream-Daten."""
    extId = metadata["mainVideoContent"]["http://zdf.de/rels/target"]["streams"]["default"]["extId"]
    stream_list_url = f"https://api.zdf.de/tmd/2/ngplayer_2_4/vod/ptmd/mediathek/{extId}"
    return fetch_json(stream_list_url, headers)

def extract_data(metadata: dict, stream_data: dict) -> tuple:
    """Extrahiert und formatiert die Daten."""
    title = metadata["title"]
    duration = format_duration(stream_data["attributes"]["duration"]["value"])
    fsk = stream_data["attributes"]["fsk"]["value"].upper()
    download_name = stream_data["priorityList"][0]["formitaeten"][0]["qualities"][0]["audio"]["tracks"][0]["uri"]
    additional_info = extract_additional_info(metadata)
    quality_options = list_quality_options(stream_data)
    return title, duration, fsk, download_name, additional_info, quality_options

def log_data(title: str, duration: str, fsk: str, download_name: str, additional_info: str, quality_options: dict):
    """Protokolliert die Daten."""
    logging.info(f"Title: {title}")
    logging.info(f"Duration: {duration}")
    logging.info(f"FSK: {fsk}")
    logging.info(f"Download URI: {download_name}")
    logging.info(f"Lead Paragraph: {additional_info}")
    logging.info("Available Qualities:")
    for quality, uri in quality_options.items():
        logging.info(f"  {quality}: {uri}")

def main(url: str):
    """Hauptfunktion."""
    if not validate_url(url):
        logging.error("Ungültige URL.")
        return
    
    base_url = url
    api_token = fetch_api_token(base_url)
    headers = {"Api-Auth": f"Bearer {api_token}"}
    
    metadata = extract_metadata(base_url, headers)
    stream_data = extract_stream_data(metadata, headers)
    data = extract_data(metadata, stream_data)
    log_data(*data)


if __name__ == "__main__":
    # Test url, nicht beachten.
    # main('https://www.zdf.de/dokumentation/zdfinfo-doku/mythos-die-groessten-raetsel-der-geschichte--drachen-100.html')
    url = input("URL: ")
    main(url)

# TODO: Clean up main in the other files.
