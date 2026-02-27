# Shroudkeeper Help / Hilfe

Dieses Dokument ist zweisprachig aufgebaut:
- Deutsch: ab Abschnitt „Deutsch“
- English: from section “English”

---

## Deutsch

### 1. Zweck des Tools

Shroudkeeper ist ein Desktop-Tool zur sicheren Verwaltung von Enshrouded-Spielständen. Es unterstützt dich dabei, Singleplayer- und Multiplayer-Daten strukturiert zu verwalten, Backups zu erstellen, Rollbacks durchzuführen und Daten zwischen lokalen und Server-Umgebungen zu übertragen.

Typische Einsatzfälle:
- Regelmäßige Sicherung von Spielständen
- Wiederherstellung eines älteren Zustands (Rollback)
- Übertragung von Save-Rolls zwischen Singleplayer und Multiplayer
- Geplante automatische Sicherungs- und Transferjobs

---

### 2. Funktionsüberblick

#### Singleplayer
- Scan lokaler World Slots
- Anzeige von Slot-Details (z. B. Latest, Größe, Änderungszeit)
- Rollback auf ältere Rolls

#### Multiplayer
- Verwaltung von Profilen für FTP, FTPS und SFTP
- Scan von Multiplayer-Daten über aktives Profil
- Rollback des Latest-Zustands auf einen gewünschten Roll

#### Transfers
- Kopieren von Save-Rolls zwischen Singleplayer und Multiplayer
- Schutzmechanismen und Hinweise bei kritischen Schreibvorgängen

#### Backups
- Erstellung lokaler Backups
- Optionale ZIP-Komprimierung
- Verwaltung vorhandener Sicherungen

#### Automationen
- Zeitgesteuerte Ausführung von Jobs
- Geeignet für wiederkehrende Backup-/Transferaufgaben

#### Einstellungen
- Sprache
- Theme
- Pfade (z. B. Backup-Ziel)

---

### 3. Systemvoraussetzungen

Für Nutzung als fertige Windows-Version:
- Windows 10 oder 11 (64 Bit)

Für Entwicklung aus dem Quellcode:
- Windows 10/11
- Python 3.11+
- PowerShell

---

### 4. Installation und Start

#### Option A: Release (empfohlen)
1. Öffne die Releases-Seite.
2. Lade die aktuelle ZIP-Datei herunter.
3. Entpacke die ZIP-Datei in einen Ordner deiner Wahl.
4. Starte Shroudkeeper.exe.

Release-Link:
- https://github.com/AmFearLiath/Shroudkeeper/releases

#### Option B: Aus Quellcode (Development)
1. Repository klonen.
2. In den Projektordner wechseln.
3. Virtuelle Umgebung erstellen.
4. Abhängigkeiten installieren.
5. Anwendung starten.

Beispielbefehle:

```powershell
cd shroudkeeper
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

---

### 5. Erste Schritte

1. Anwendung starten.
2. Unter Einstellungen Sprache und ggf. Backup-Pfad prüfen.
3. Singleplayer-Root konfigurieren (falls nicht automatisch erkannt).
4. Zuerst einen Scan durchführen.
5. Vor jeder Schreiboperation ein Backup erstellen.

Empfehlung:
- Vor Transfer, Rollback oder Restore immer eine Sicherung erzeugen.

---

### 6. Multiplayer-Profile einrichten

Ein Profil enthält die Zugangsdaten zu deinem Server-Speicher.

Benötigte Angaben:
- Name
- Protokoll (FTP, FTPS oder SFTP)
- Host
- Port
- Benutzername
- Remote-Pfad

Hinweise:
- Bei FTPS/SFTP müssen die jeweiligen Verbindungsdaten korrekt sein.
- Vor Schreiboperationen auf dem Zielserver den Serverprozess stoppen.

---

### 7. Sicher arbeiten (wichtig)

#### Vor jeder Schreiboperation
- Backup erstellen
- Prüfen, ob das richtige Ziel ausgewählt ist
- Änderungen bewusst und nachvollziehbar durchführen

#### Bei lokalen Schreibvorgängen
- Enshrouded sollte geschlossen sein

#### Bei Multiplayer-Schreibvorgängen
- Zielserver vorher stoppen

---

### 8. Backup und Wiederherstellung

Empfohlener Ablauf:
1. Backup erstellen
2. Integrität grob prüfen (Dateien vorhanden, Größe plausibel)
3. Erst danach Transfer/Rollback/Restore ausführen

Wenn ein Fehler auftritt:
- Keine weiteren Schreibvorgänge starten
- Letztes funktionierendes Backup wiederherstellen

---

### 9. Automationen

Mit Automationen lassen sich wiederkehrende Jobs planen.

Typische Nutzung:
- Tägliche Multiplayer-Backups
- Zeitgesteuerte Uploads

Empfehlungen:
- Automationen zunächst manuell testen
- In produktiven Szenarien nur stabile Profile und Pfade verwenden

---

### 10. Fehlerbehebung

#### Anwendung startet nicht
- Prüfen, ob alle Dateien aus der ZIP vollständig entpackt wurden
- Falls aus Quellcode: Abhängigkeiten erneut installieren

#### Verbindungstest zum Server schlägt fehl
- Host, Port, Benutzername und Protokoll kontrollieren
- Netzwerk/Firewall prüfen
- Bei SFTP/FTPS Zugangsdaten und Serverseite prüfen

#### Keine Savegames gefunden
- Singleplayer-Root-Pfad kontrollieren
- Berechtigungen prüfen
- Erneut scannen

#### Transfer/Rollback schlägt fehl
- Sicherstellen, dass Spiel bzw. Zielserver gestoppt ist
- Schreibrechte prüfen
- Backup-Ordner und Zielpfad prüfen

---

### 11. Daten und Datenschutz

- App-Daten werden unter %APPDATA%/Shroudkeeper gespeichert.
- Das Tool legt keine dauerhaften Nutzerdaten im Installationsordner an.
- Sensible Server-Zugangsdaten sollten nur über die vorgesehenen Mechanismen verwaltet werden.

---

### 12. Build-Hinweise für Maintainer

Standard-Build:

```powershell
cd shroudkeeper
pyinstaller --noconfirm Shroudkeeper.spec
```

Release-Packaging (Projekt-Skript):

```powershell
.\scripts\create-release.ps1 -Version "1.0.0"
```

Das Skript erstellt:
- ZIP-Paket
- SHA256-Datei
- Release-Notes-Datei

---

### 13. Haftungsausschluss

Die Nutzung erfolgt auf eigene Verantwortung. Trotz sorgfältiger Entwicklung sind Datenverlust oder beschädigte Spielstände durch Fehlbedienung, Systemfehler oder externe Umstände nicht vollständig auszuschließen.

---

### 14. Support und Links

- GitHub Repository: https://github.com/AmFearLiath/Shroudkeeper
- Releases: https://github.com/AmFearLiath/Shroudkeeper/releases


---
---

## English

### 1. Purpose of the tool

Shroudkeeper is a desktop tool for safer Enshrouded savegame management. It helps you organize singleplayer and multiplayer data, create backups, perform rollbacks, and transfer data between local and server environments.

Typical use cases:
- Regular savegame backups
- Restoring an older state (rollback)
- Copying save rolls between singleplayer and multiplayer
- Scheduled automatic backup/transfer jobs

---

### 2. Feature overview

#### Singleplayer
- Scan local world slots
- View slot details (for example latest, size, modification time)
- Roll back to older rolls

#### Multiplayer
- Manage FTP, FTPS, and SFTP profiles
- Scan multiplayer data via active profile
- Roll back latest state to a selected roll

#### Transfers
- Copy save rolls between singleplayer and multiplayer
- Built-in warnings for critical write operations

#### Backups
- Create local backups
- Optional ZIP compression
- Manage existing backup entries

#### Automations
- Schedule recurring jobs
- Useful for regular backup/transfer workflows

#### Settings
- Language
- Theme
- Paths (for example backup target)

---

### 3. System requirements

For packaged Windows release usage:
- Windows 10 or 11 (64-bit)

For development from source:
- Windows 10/11
- Python 3.11+
- PowerShell

---

### 4. Installation and launch

#### Option A: Release build (recommended)
1. Open the releases page.
2. Download the latest ZIP file.
3. Extract the ZIP archive.
4. Start Shroudkeeper.exe.

Release link:
- https://github.com/AmFearLiath/Shroudkeeper/releases

#### Option B: From source (development)
1. Clone the repository.
2. Change to project directory.
3. Create a virtual environment.
4. Install dependencies.
5. Start the app.

Example commands:

```powershell
cd shroudkeeper
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

---

### 5. Quick start

1. Launch the application.
2. Check language and backup path in Settings.
3. Configure singleplayer root if it is not auto-detected.
4. Run an initial scan.
5. Create a backup before any write operation.

Recommendation:
- Always create a backup before transfer, rollback, or restore.

---

### 6. Multiplayer profile setup

A profile stores your server access settings.

Required fields:
- Name
- Protocol (FTP, FTPS, or SFTP)
- Host
- Port
- Username
- Remote path

Notes:
- FTPS/SFTP requires valid remote access settings.
- Stop the target server process before write operations.

---

### 7. Safe operation guidelines

#### Before any write operation
- Create a backup
- Verify selected target
- Perform changes intentionally and traceably

#### For local writes
- Enshrouded should be closed

#### For multiplayer writes
- Stop the target server first

---

### 8. Backup and restore workflow

Recommended sequence:
1. Create backup
2. Verify basic integrity (files exist, size looks plausible)
3. Execute transfer/rollback/restore only afterwards

If an error occurs:
- Do not continue with additional writes
- Restore the latest known-good backup

---

### 9. Automations

Automations let you schedule recurring jobs.

Typical use:
- Daily multiplayer backups
- Scheduled uploads

Recommendations:
- Test jobs manually first
- Use only validated profiles and paths for production-like usage

---

### 10. Troubleshooting

#### App does not start
- Confirm all files were extracted from ZIP
- If running from source: reinstall dependencies

#### Server connection test fails
- Check host, port, username, and protocol
- Check network/firewall
- Validate SFTP/FTPS settings on server side

#### No savegames found
- Verify singleplayer root path
- Check filesystem permissions
- Run scan again

#### Transfer/rollback fails
- Ensure game or target server is stopped
- Verify write permissions
- Check backup and destination paths

---

### 11. Data and privacy

- App data is stored under %APPDATA%/Shroudkeeper.
- No persistent user data is intended in the installation directory.
- Handle sensitive server credentials only via intended app mechanisms.

---

### 12. Build notes for maintainers

Standard build:

```powershell
cd shroudkeeper
pyinstaller --noconfirm Shroudkeeper.spec
```

Release packaging (project script):

```powershell
.\scripts\create-release.ps1 -Version "1.0.0"
```

The script generates:
- ZIP package
- SHA256 file
- Release notes file

---

### 13. Disclaimer

Use at your own risk. Despite careful development, data loss or corrupted savegames caused by user error, system issues, or external circumstances cannot be fully ruled out.

---

### 14. Support and links

- GitHub repository: https://github.com/AmFearLiath/Shroudkeeper
- Releases: https://github.com/AmFearLiath/Shroudkeeper/releases
