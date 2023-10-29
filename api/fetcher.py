import requests
import re

def fetch_api_token(url: str) -> str:
    """Holt API-Token."""
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Fehler beim Abrufen des API-Tokens.")
    return re.search(r'window\.zdfsite\.player\.apiToken = "([\d\w]+)";', response.text)[1]

def fetch_json(url: str, headers: dict) -> dict:
    """Holt JSON-Daten."""
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Fehler beim Abrufen von JSON von {url}.")
    return response.json()
