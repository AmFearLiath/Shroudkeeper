# Singleplayer (EN)

## 1) Configure savegame directory (if auto-detect fails)

1. Open **Settings**.
2. Locate **Singleplayer Save Root**.
3. Click **Browse** and select the correct Enshrouded save folder.
4. Apply/Save settings.
5. Go to **Singleplayer** and run a new **Scan**.

### How to verify the correct path

- World slots appear after scanning.
- Slot data such as name, world ID, size, and modified time is visible.
- If no slots are found, verify path/permissions and scan again.

## 2) Understanding the detail view

The slot detail view shows:

- Slot number and world name
- World ID
- Current `latest` roll
- Individual rolls with existence, size, and modified timestamp
- Warnings from the scan

Use this view to confirm the target roll before rollback.

## 3) Performing rollback

Rollback re-points a slot `latest` reference to an older roll.

Recommended sequence:

1. Create a backup.
2. Close the game.
3. Select the desired roll in slot details.
4. Execute **Rollback** and review confirmation dialog.
5. Verify result in status and refreshed data.

## Common issues

- Game still running → close it before local writes.
- Wrong path → scan returns no data.
- Missing rights → check folder permissions.