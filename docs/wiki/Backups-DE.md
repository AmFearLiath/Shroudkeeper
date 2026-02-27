# Backups (DE)

## Zweck

Backups sichern deinen aktuellen Stand vor riskanten Änderungen.

## 1) Singleplayer-Backup

1. In den Bereich **Backups** wechseln.
2. **Singleplayer Backup** wählen.
3. Einzelnen Slot oder alle Slots auswählen.
4. Backup erstellen.

## 2) Multiplayer-Backup

1. Aktives oder ausgewähltes Multiplayer-Profil prüfen.
2. **Multiplayer Backup** ausführen.
3. Ergebnis im Status prüfen.

## 3) Optionen

- Backup als ZIP erstellen
- Unkomprimierten Ordner zusätzlich behalten

## 4) Restore aus Backup (neu)

In der Backup-Liste gibt es pro Eintrag die Aktion **Wiederherstellen**.

Ablauf:
1. **Wiederherstellen** klicken.
2. Ziel wählen: **Singleplayer** oder **Multiplayer**.
3. Bei Singleplayer den **Ziel-Slot** auswählen.
4. Bei Multiplayer das **Ziel-Profil** auswählen.
5. Sicherheitsabfrage bestätigen.

Sicherheitschecks:
- Singleplayer: Wiederherstellung wird blockiert, wenn `enshrouded.exe` läuft.
- Multiplayer: Es wird ein Hinweis angezeigt, dass der Zielserver gestoppt sein soll.

## 5) Wiederherstellungsempfehlung

- Vor Restore Zielzustand prüfen.
- Wenn möglich, vor Restore nochmals ein aktuelles Sicherungsbackup erzeugen.

## Best Practice

- Vor jedem Rollback/Transfer ein Backup.
- Benenne/ordne Backups nachvollziehbar (Datum, Zweck).
- Regelmäßig testen, ob Wiederherstellung funktioniert.