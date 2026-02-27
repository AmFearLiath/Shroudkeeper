# Singleplayer (DE)

## 1) Savegame-Verzeichnis einrichten (wenn Auto-Detect fehlschlägt)

1. Öffne **Settings**.
2. Suche den Eintrag **Singleplayer Save Root**.
3. Klicke auf **Durchsuchen** und wähle den korrekten Enshrouded-Save-Ordner.
4. Übernimm/Speichere die Einstellungen.
5. Wechsle auf **Singleplayer** und starte einen neuen **Scan**.

### Woran erkenne ich den korrekten Pfad?

- Nach dem Scan werden World Slots angezeigt.
- Slot-Daten wie Name, World ID, Größe und letzte Änderung sind sichtbar.
- Wenn keine Slots gefunden werden: Pfad/Berechtigungen prüfen und erneut scannen.

## 2) Detailseite verstehen

Die Detailansicht zeigt je ausgewähltem Slot:

- Slot-Nummer und World-Name
- World ID
- Aktuellen `latest`-Roll
- Einzelne Rolls mit Existenz, Größe und Änderungszeit
- Warnungen/Hinweise aus dem Scan

Nutze die Detailseite, um vor einem Rollback den richtigen Ziel-Roll zu prüfen.

## 3) Rollback durchführen

Rollback setzt den `latest`-Verweis eines Slots auf einen älteren Roll.

Empfohlener Ablauf:

1. Backup erstellen.
2. Spiel schließen.
3. In den Slot-Details den gewünschten Roll auswählen.
4. **Rollback ausführen** und Bestätigungsdialog prüfen.
5. Ergebnis prüfen (Statusmeldung + aktualisierte Anzeige).

## Typische Probleme

- Spiel läuft noch → lokal nicht schreiben, erst schließen.
- Falscher Pfad → Scan findet keine Daten.
- Fehlende Rechte → Ordnerzugriff prüfen.