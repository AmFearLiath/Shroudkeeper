# Backups (EN)

## Purpose

Backups protect your current state before risky operations.

## 1) Singleplayer backup

1. Open **Backups** section.
2. Select **Singleplayer Backup**.
3. Choose one slot or all slots.
4. Create backup.

## 2) Multiplayer backup

1. Verify active/selected multiplayer profile.
2. Run **Multiplayer Backup**.
3. Check completion status.

## 3) Options

- Create backup as ZIP
- Keep additional uncompressed folder

## 4) Restore from backup (new)

Each backup entry now provides a **Restore** action.

Workflow:
1. Click **Restore**.
2. Choose target: **Singleplayer** or **Multiplayer**.
3. For singleplayer, select the **target slot**.
4. For multiplayer, select the **target profile**.
5. Confirm the safety prompt.

Safety checks:
- Singleplayer: restore is blocked while `enshrouded.exe` is running.
- Multiplayer: a warning reminds you to stop the target server before writing.

## 5) Restore recommendation

- Verify target state before restore.
- If possible, create one fresh safety backup before restoring.

## Best practice

- Backup before every rollback/transfer.
- Keep clear naming/order (date and intent).
- Regularly test restore workflow.