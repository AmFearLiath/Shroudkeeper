# Shroudkeeper

Shroudkeeper ist ein Python 3.12+ Desktop-Projekt auf Basis von PySide6.
Die Architektur trennt Core, Storage, i18n und UI klar voneinander und ist auf spätere Erweiterungen vorbereitet (Scanner, Transfer-Engine, Remote-Adapter, Scheduler).

## Features

- Zentrales i18n-System mit Runtime-Sprachwechsel
- Build-sicheres Ressourcenladen über `resource_path()`
- SQLite-Datenbank im AppData-Ordner mit `schema.sql`-Initialisierung
- Konfigurationsspeicherung als JSON im AppData-Ordner
- Rotierendes Datei-Logging plus Live-Log-Ausgabe im UI
- Theme-Laden über QSS aus den Assets

## Entwicklung starten

1. Python 3.12+ installieren
2. Abhängigkeiten installieren:
   - `pip install -r requirements.txt`
3. Anwendung starten:
   - `python app.py`

## PyInstaller-Hinweis

Das Projekt ist so aufgebaut, dass Ressourcen (`storage/schema.sql`, `assets/themes`, `i18n/translations`, `assets/icons`) über `resource_path()` auch im PyInstaller-Bundle aufgelöst werden.
Beim Build müssen diese Dateien/Ordner als Daten mitgegeben werden.

## Strukturübersicht

```text
embervault/
  app.py
  __init__.py
  core/
    config.py
    logging.py
    paths.py
    resources.py
  storage/
    db.py
    repositories.py
    schema.sql
  i18n/
    i18n.py
    translations/
      de.json
      en.json
  ui/
    main_window.py
    navigation.py
    views/
      dashboard_view.py
      transfers_view.py
      backups_view.py
      automations_view.py
      profiles_view.py
      settings_view.py
    widgets/
      log_console.py
  assets/
    themes/
      embervault.qss
    icons/
  README.md
  requirements.txt
```
