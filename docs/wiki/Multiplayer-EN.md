# Multiplayer & Configurator (EN)

## 1) Set up multiplayer profile

1. Open **Profiles**.
2. Click **Add profile**.
3. Provide:
   - Name
   - Protocol (`FTP`, `FTPS`, or `SFTP`)
   - Host, Port
   - Username
   - Remote path
4. Enter password (store if desired).
5. Run **Connection test**.
6. Set profile as active.

## 2) Multiplayer detail view

After a successful scan, the detail view typically shows:

- World ID
- Remote path
- Current `latest` roll
- Rolls (file, size, timestamp, exists/missing)
- Warnings

## 3) Multiplayer rollback

Rollback moves `latest` to an older roll.

Safe sequence:

1. Stop server.
2. Create backup.
3. Select target roll.
4. Confirm rollback.
5. Optionally rescan and verify results.

## 4) Multiplayer configurator

The configurator edits server-side configuration files.

Main sections:

- Basic data (name, save/log path, query port, slot count)
- Voice/text chat
- Gameplay/GameSettings
- Usergroups/permissions
- Bans

Typical workflow:

1. Load configuration.
2. Edit in form or JSON tab.
3. Check validation.
4. Save.
5. Start server with updated config.

Tip: test major configuration changes on a staging server first.