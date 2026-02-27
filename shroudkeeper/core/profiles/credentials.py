from __future__ import annotations

import keyring


class CredentialService:
    _SERVICE_NAME = "Shroudkeeper"

    def _credential_key(self, profile_id: int, username: str) -> str:
        return f"profile:{profile_id}:user:{username}"

    def set_password(self, profile_id: int, username: str, password: str) -> None:
        keyring.set_password(self._SERVICE_NAME, self._credential_key(profile_id, username), password)

    def get_password(self, profile_id: int, username: str) -> str | None:
        return keyring.get_password(self._SERVICE_NAME, self._credential_key(profile_id, username))

    def delete_password(self, profile_id: int, username: str) -> None:
        key = self._credential_key(profile_id, username)
        try:
            keyring.delete_password(self._SERVICE_NAME, key)
        except keyring.errors.PasswordDeleteError:
            pass
