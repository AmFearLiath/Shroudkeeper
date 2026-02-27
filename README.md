# Shroudkeeper

Desktop-Tool zur Verwaltung, Sicherung, Übertragung und Automatisierung von Enshrouded-Spielständen.

## Features

- Singleplayer-Slots scannen und verwalten
- Multiplayer-Profile (FTP/FTPS/SFTP) verwalten
- Transfers zwischen Singleplayer und Multiplayer durchführen
- Backups erstellen und verwalten
- Cron-basierte Automationen für Server-Backups/Deployments
- Mehrsprachige Oberfläche (u. a. DE, EN, RU, FR, IT, ES, PT, PL, BG, CS, TR, ZH, JA, VI)
- Windows-Distribution als ausführbare Datei (PyInstaller)

## Projektstruktur

```text
shroudkeeper/
	app.py
	assets/
	core/
	i18n/
	storage/
	ui/
```

## Voraussetzungen (Entwicklung)

- Windows 10/11
- Python 3.11+
- PowerShell

## Installation (Development)

```powershell
cd shroudkeeper
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

## Build (Windows)

Standard OneDir-Build:

```powershell
cd shroudkeeper
pyinstaller --noconfirm Shroudkeeper.spec
```

Output:

- `shroudkeeper/dist/Shroudkeeper/Shroudkeeper.exe`
- plus benötigter Runtime-Ordner (`_internal`)

## Konfiguration & Daten

- Nutzerdaten werden unter `%APPDATA%/Shroudkeeper` gespeichert.
- Es werden keine Nutzerdaten im Installationsordner persistiert.

## Sicherheitshinweise

- Vor Schreiboperationen (Transfer/Rollback/Restore) immer Backup erstellen.
- Beim Schreiben in Multiplayer-Dateien den Zielserver vorher stoppen.
- Bei lokalen Schreiboperationen Enshrouded schließen.

## Lokalisierung

- Sprachdateien liegen in `shroudkeeper/i18n/translations/*.json`.
- Neue Texte werden über i18n-Keys gepflegt.

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Details inklusive Third-Party-Liste stehen in der Datei `LICENSE`.

## Third-Party

Verwendete Hauptbibliotheken:

- PySide6
- keyring
- aioftp
- asyncssh
- zstandard
- APScheduler
- croniter
- psutil

## Haftungsausschluss

Shroudkeeper ist ein Community-Projekt und steht in keiner offiziellen Verbindung zu Keen Games oder Enshrouded.

