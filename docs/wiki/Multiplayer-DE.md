# Multiplayer & Konfigurator (DE)

## 1) Multiplayer-Profil einrichten

1. Öffne **Profiles**.
2. Klicke auf **Profil hinzufügen**.
3. Trage ein:
   - Name
   - Protokoll (`FTP`, `FTPS` oder `SFTP`)
   - Host, Port
   - Benutzername
   - Remote-Pfad
4. Passwort eingeben (bei Bedarf speichern).
5. **Verbindung testen**.
6. Profil als aktiv setzen.

## 2) Multiplayer-Detailseite

Nach erfolgreichem Scan zeigt die Detailseite typischerweise:

- World ID
- Remote-Pfad
- Aktueller `latest`-Roll
- Rolls (Datei, Größe, Zeitstempel, vorhanden/nicht vorhanden)
- Warnungen/Hinweise

## 3) Multiplayer-Rollback

Rollback setzt `latest` auf einen älteren Roll.

Sicherer Ablauf:

1. Server stoppen.
2. Backup erstellen.
3. Ziel-Roll wählen.
4. Rollback bestätigen.
5. Danach optional erneut scannen und Ergebnis prüfen.

## 4) Multiplayer-Konfigurator

Der Konfigurator dient zur Bearbeitung serverseitiger Konfigurationsdateien.

Wesentliche Bereiche:

- Basisdaten (Name, Save-/Log-Pfad, Query-Port, Slots)
- Voice-/Text-Chat
- Gameplay/GameSettings
- Usergroups/Permissions
- Bans

Typischer Workflow:

1. Konfiguration laden.
2. Änderungen im Formular oder JSON-Tab vornehmen.
3. Validierung prüfen.
4. Speichern.
5. Server mit neuer Konfiguration starten.

Hinweis: Größere Änderungen zuerst an einem Testserver prüfen.