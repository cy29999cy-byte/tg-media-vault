"""Telegram authentication/session wrapper for TG Media Vault.

This module deliberately keeps authentication separate from the downloader so the
UI can drive phone-code/password login without exposing Telethon details.
"""

from pathlib import Path
from typing import Optional, Union

from telethon import TelegramClient


class TelegramSession:
    """Small async wrapper around a persistent Telethon session."""

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_path: Union[str, Path],
    ) -> None:
        path = Path(session_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._client = TelegramClient(str(path), api_id=api_id, api_hash=api_hash)

    @property
    def client(self) -> TelegramClient:
        return self._client

    async def connect(self) -> None:
        if not self._client.is_connected():
            await self._client.connect()

    async def disconnect(self) -> None:
        if self._client.is_connected():
            await self._client.disconnect()

    async def is_authorized(self) -> bool:
        await self.connect()
        return await self._client.is_user_authorized()

    async def send_code(self, phone: str) -> str:
        """Send a Telegram login code and return the phone-code hash."""
        await self.connect()
        sent = await self._client.send_code_request(phone)
        return sent.phone_code_hash

    async def sign_in_code(
        self,
        phone: str,
        code: str,
        phone_code_hash: Optional[str] = None,
    ):
        """Complete login with the SMS/app code.

        Telethon may raise SessionPasswordNeededError when 2FA is enabled; the UI
        should then request the Telegram password and call ``sign_in_password``.
        """
        await self.connect()
        return await self._client.sign_in(
            phone=phone,
            code=code,
            phone_code_hash=phone_code_hash,
        )

    async def sign_in_password(self, password: str):
        """Complete Telegram two-step verification."""
        await self.connect()
        return await self._client.sign_in(password=password)

    async def account_id(self) -> str:
        """Return the authorized Telegram account id as a stable string."""
        await self.connect()
        me = await self._client.get_me()
        if me is None:
            raise RuntimeError("Telegram account is not authorized")
        return str(me.id)
