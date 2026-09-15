# ZDF-LinkFinder

ZDF-LinkFinder ist ein command-line Tool zum Herunterladen von Videos aus der ZDF Mediathek.

## Übersicht

ZDF-LinkFinder ermöglicht den einfachen Download von Videos/ Filmen in verschiedenen Qualitätsstufen direkt über die Kommandozeile aus der ZDF Mediathek. Das Tool übernimmt automatisch die Auswahl der besten verfügbaren Qualität, bietet Multi-threading für hohe Downloadgeschwindigkeiten.

## Funktionen

- Download von "Medien" aus der ZDF Mediathek
- Schnelle Downloads durch Multi-threading
- Fortschrittsanzeige mit Geschwindigkeitsanzeige (Progress bar)
- Unterstützung für direkte Formate (MP4, WebM) und adaptive Streaming-Formate (M3U8)
- Parallele, verbindungsgepoolte Serien- und Episodenerkennung mit begrenzter Anfragenzahl

## Installation

1. Repository klonen:

```bash
git clone https://github.com/EvickaStudio/ZDF-LinkFinder.git
cd ZDF-LinkFinder
```

1. Virtual Environment erstellen, aktivieren und Abhängigkeiten installieren:

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# oder via UV mit:
uv sync
```

## Benutzung

### Basisnutzung

Film herunterladen. Ohne Qualitätsoption erscheint eine Auswahl; Enter wählt die höchste verfügbare Qualität:

```bash
uv run main.py https://www.zdf.de/filme/bis-es-blutet-movie-100
```

Eine Serienseite zeigt zuerst die vorhandenen Staffeln und danach die verfügbaren Episoden. Bei beiden Auswahlen werden einzelne Nummern, Listen, Bereiche und `all` akzeptiert:

```bash
uv run main.py https://www.zdf.de/serien/inspector-ikmen-tod-in-istanbul-100
```

Beispiele für gültige Eingaben sind `2`, `1,3`, `1-3` und `all`. Die Episoden werden mit einer Auswahl-ID und ihrer tatsächlichen Kennzeichnung wie `S01E04` angezeigt. ZDF stellt nicht immer jede produzierte Folge einer Staffel zum Abruf bereit; angeboten werden nur aktuell herunterladbare Folgen.

### Kommandozeilenoptionen

```
usage: main.py [-h] [-q QUALITY] [-o OUTPUT] [-t THREADS] [-v] [-f] [-l] [-b]
               [--seasons SELECTION] [--episodes SELECTION] [url]

positional arguments:
  url                   URL des ZDF-Videos

options:
  -h, --help            Hilfetext anzeigen
  -q QUALITY, --quality QUALITY
                        Qualität wählen, zum Beispiel 1080p50 oder veryhigh
  -o OUTPUT, --output OUTPUT
                        Dateiname festlegen (Standard: [title]_[quality].[format])
  -t THREADS, --threads THREADS
                        Anzahl paralleler Downloads (Standard: 4)
  -v, --verbose         Ausführliche Ausgabe aktivieren
  -f, --force           Existierende Dateien überschreiben
  -l, --list-qualities  Verfügbare Qualitäten anzeigen, ohne herunterzuladen
  -b, --best            Höchste verfügbare Qualität ohne Nachfrage auswählen
  --seasons SELECTION   Staffeln: all, 1, 1-3 oder 1,3
  --episodes SELECTION  Episoden-IDs nach der Staffelauswahl: all, 1, 1-3 oder 1,3
```

### Beispiele

- **Qualitätsoptionen anzeigen:**

```bash
uv run main.py https://www.zdf.de/filme/bis-es-blutet-movie-100 --list-qualities
```

- **Herunterladen in bestimmter Qualität:**

```bash
uv run main.py https://www.zdf.de/filme/bis-es-blutet-movie-100 --quality 1080p50
```

- **Beste Qualität automatisch wählen:**

```bash
uv run main.py https://www.zdf.de/filme/bis-es-blutet-movie-100 --best
```

- **Dateinamen festlegen:**

```bash
uv run main.py https://www.zdf.de/filme/bis-es-blutet-movie-100 -o my_video.mp4
```

- **Download-Geschwindigkeit erhöhen (mehr Threads):**

```bash
uv run main.py https://www.zdf.de/filme/bis-es-blutet-movie-100 --threads 8
```

- **Ausführliche Log-Ausgabe:**

```bash
uv run main.py https://www.zdf.de/filme/bis-es-blutet-movie-100 -v
```

- **Staffeln 1 bis 3 vollständig herunterladen:**

```bash
uv run main.py https://www.zdf.de/serien/die-toten-vom-bodensee-132 --seasons 1-3 --episodes all --best
```

- **Bestimmte Einträge aus Staffel 2 auswählen:**

```bash
uv run main.py https://www.zdf.de/serien/die-toten-vom-bodensee-132 --seasons 2 --episodes 1,3-4
```

## Hinweise

- Vorhandene Dateien werden standardmäßig nicht überschrieben, außer die Option `--force` wird genutzt.
- Die Option `--best` wählt automatisch die höchste verfügbare Qualität aus.
- Ohne `--quality` oder `--best` zeigt das Tool im Terminal eine Qualitätsauswahl. Die Vorauswahl ermittelt für jedes ausgewählte Video einzeln die höchste verfügbare Auflösung und Bildrate.
- Eine ausdrücklich gewählte Auflösung wie `720p50` wird auf alle ausgewählten Episoden angewendet. Ist sie bei einer Episode nicht verfügbar, verwendet das Tool dort deren beste verfügbare Qualität.
- Bei einer Serienseite werden Staffeln und Episoden interaktiv ausgewählt. Ohne interaktive Eingabe wird die neueste Staffel vollständig verarbeitet; `--seasons` und `--episodes` steuern Batch-Aufrufe.
- `--output` kann bei einer Serie verwendet werden, wenn genau eine Episode ausgewählt wurde. Automatische Dateinamen beginnen mit `SxxExx_`.
- Adaptive Streaming-Formate (M3U8) werden mit dem durch `imageio-ffmpeg` bereitgestellten FFmpeg verlustfrei in eine MP4-Datei umgepackt.

## Format-Einschränkungen

Die ZDF Mediathek bietet mehrere Videoformate an:

- **Direkt herunterladbare Formate** (MP4, WebM): Diese werden unterstützt.
- **Streaming-Formate** (M3U8): Adaptive Playlists bis zur höchsten angebotenen Auflösung, unterstützt über FFmpeg.

ZDFs ältere Qualitätsnamen entsprechen nicht direkt einer Auflösung: `veryhigh` kann beispielsweise nur 960×540 sein. Die Auflösungsoptionen wie `1080p50` sind eindeutig.

<!-- ## Screenshots -->

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).
