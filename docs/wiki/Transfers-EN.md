# Transfers (EN)

Transfers copy save rolls between singleplayer and multiplayer.

## 1) Prepare transfer

1. Select source and target.
2. Choose slot and roll.
3. Ensure source and target are not identical.
4. For multiplayer target: stop server.
5. Create backup.

## 2) Run transfer

1. Click **Start transfer**.
2. Review warnings/confirmations.
3. Follow status updates (preparing, copying, writing index, done).

## 3) Post-check

- Rescan destination side.
- Verify `latest` and roll files were applied as expected.
- If needed, restore last known-good backup.

## Common errors

- No active profile (for multiplayer).
- Game/server still running.
- Missing write permissions.
- Invalid direction or incomplete selection.