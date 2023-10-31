# ZDF-LinkFinder
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Beschreibung:

ZDF-LinkFinder ist ein CLI-Tool zur Extraktion von Download-Links für Videos aus der ZDF-Mediathek. Das Tool gibt die verfügbaren Qualitätsstufen und die dazugehörigen Download-Links aus. Links können auch direkt heruntergeladen werden. Auch kann hiermit die Altersverifikation umgangen werden, da die Links zu akamai gehören und ohne eischränkungen funktionieren.

## Abhängigkeiten:
- Python 3.x
- `requests`
- `re` (Reguläre Ausdrücke)


## Installation:
1. Klonen Sie das Repository.
2. Installieren Sie die erforderlichen Pakete mit `pip install -r requirements.txt`.

## Benutzung:
Führen Sie `main.py` aus und geben Sie die URL des gewünschten ZDF-Mediathek Films/ Serie etc. ein. Das Tool gibt die verfügbaren Qualitätsstufen und die dazugehörigen Download-Links aus.

```bash
python main.py
```

## Screenshots:

Beispiel Ausgabe (vps):
![Screenshot](assets/screenshot.png)

## Lizenz:
Dieses Projekt steht unter der MIT-Lizenz. Siehe [LICENSE](LICENSE) für weitere Informationen.