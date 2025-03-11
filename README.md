# ZDF-LinkFinder

ZDF-LinkFinder ist ein command-line Tool zum Herunterladen von Videos aus der ZDF Mediathek.

## Übersicht

ZDF-LinkFinder ermöglicht den einfachen Download von Videos/ Filmen in verschiedenen Qualitätsstufen direkt über die Kommandozeile aus der ZDF Mediathek. Das Tool übernimmt automatisch die Auswahl der besten verfügbaren Qualität, bietet Multi-threading für hohe Downloadgeschwindigkeiten.

## Funktionen

- Download von "Medien" aus der ZDF Mediathek
- Schnelle Downloads durch Multi-threading
- Fortschrittsanzeige mit Geschwindigkeitsanzeige (Progress bar)
- Unterscheidung zwischen direkt herunterladbaren Formaten (MP4, WebM) und nicht unterstützten Streaming-Formaten (M3U8), da es gerade keine m3u8 Unterstützung gibt.

## Installation

1. Repository klonen:

```bash
git clone https://github.com/EvickaStudio/ZDF-LinkFinder.git
cd ZDF-LinkFinder
```

2. Virtual Environment erstellen und aktivieren (optional):

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. Abhängigkeiten installieren:

Dies ist in dem Fall nur `requests`, eine Bibliothek für HTTP anfragen

```bash
pip install -r requirements.txt
```

## Benutzung

### Basisnutzung

Video mit Standardqualität (`veryhigh`) herunterladen:

```bash
python main.py https://www.zdf.de/serien/the-rookie/neue-wege-112.html
```

### Kommandozeilenoptionen

```
usage: main.py [-h] [-q QUALITY] [-o OUTPUT] [-t THREADS] [-v] [-f] [-l] [-b] [url]

positional arguments:
  url                   URL des ZDF-Videos

options:
  -h, --help            Hilfetext anzeigen
  -q QUALITY, --quality QUALITY
                        Qualität wählen (Standard: veryhigh)
  -o OUTPUT, --output OUTPUT
                        Dateiname festlegen (Standard: [title]_[quality].mp4)
  -t THREADS, --threads THREADS
                        Anzahl paralleler Downloads (Standard: 4)
  -v, --verbose         Ausführliche Ausgabe aktivieren
  -f, --force           Existierende Dateien überschreiben
  -l, --list-qualities  Verfügbare Qualitäten anzeigen, ohne herunterzuladen
  -b, --best            Beste direkt herunterladbare Qualität automatisch auswählen
```

### Beispiele

- **Qualitätsoptionen anzeigen:**

```bash
python main.py https://www.zdf.de/serien/example-show/episode-123.html --list-qualities
```

- **Herunterladen in bestimmter Qualität:**

```bash
python main.py https://www.zdf.de/serien/example-show/episode-123.html --quality high
```

- **Beste Qualität automatisch wählen:**

```bash
python main.py https://www.zdf.de/serien/example-show/episode-123.html --best
```

- **Dateinamen festlegen:**

```bash
python main.py https://www.zdf.de/serien/example-show/episode-123.html -o my_video.mp4
```

- **Download-Geschwindigkeit erhöhen (mehr Threads):**

```bash
python main.py https://www.zdf.de/serien/example-show/episode-123.html --threads 8
```

- **Ausführliche Log-Ausgabe:**

```bash
python main.py https://www.zdf.de/serien/example-show/episode-123.html -v
```

## Hinweise

- Vorhandene Dateien werden standardmäßig nicht überschrieben, außer die Option `--force` wird genutzt.
- Die Option `--best` wählt automatisch die höchste verfügbare Qualität aus, die direkt herunterladbar ist.
- Streaming-Formate (M3U8) sind nicht zum direkten Download geeignet und werden vom Tool automatisch ignoriert.

## Format-Einschränkungen

Die ZDF Mediathek bietet zwei Videoformate an:

- **Direkt herunterladbare Formate** (MP4, WebM): Diese werden unterstützt.
- **Streaming-Formate** (M3U8): Adaptive Playlists, nicht unterstützt.

Das Tool informiert automatisch, falls eine nicht unterstützte Qualität gewählt wurde.

<!-- ## Screenshots -->

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).
