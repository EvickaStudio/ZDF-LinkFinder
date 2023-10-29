def extract_additional_info(metadata: dict) -> str:
    """Extrahiert zusätzliche Informationen."""
    return metadata.get("leadParagraph")

def list_quality_options(stream_data: dict) -> dict:
    """Listet verfügbare Qualitätsstufen."""
    qualities = {}
    for item in stream_data['priorityList']:
        for form in item['formitaeten']:
            for quality in form['qualities']:
                quality_name = quality['quality']
                download_uri = quality['audio']['tracks'][0]['uri']
                qualities[quality_name] = download_uri
    return qualities
