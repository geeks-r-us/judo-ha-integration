"""Cloud authentication helper for Judo client."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class CloudAuthenticator:
    """Manage cloud token login/refresh."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        username: str | None,
        password: str | None,
        timeout: int,
    ) -> None:
        self._session = session
        self._base_url = base_url
        self._username = username
        self._password = password
        self._timeout = timeout
        self._token: str | None = None

    @property
    def token(self) -> str | None:
        """Return current token if available."""
        return self._token

    async def authenticate(self) -> str:
        """Authenticate and return token."""
        if not self._username or not self._password:
            raise ValueError("Username and password required for cloud authentication")

        payload = {
            "group": "register",
            "command": "login",
            "name": "login",
            "user": self._username,
            "password": hashlib.md5(self._password.encode("utf-8")).hexdigest(),
            "nohash": "Service",
            "role": "customer",
        }

        timeout = aiohttp.ClientTimeout(total=self._timeout)
        async with self._session.get(self._base_url, params=payload, timeout=timeout) as response:
            response.raise_for_status()
            data: dict[str, Any] = await response.json(content_type=None)

        token = data.get("token")
        if not token:
            raise RuntimeError(f"Cloud authentication failed: {data}")

        self._token = str(token)
        _LOGGER.debug("Cloud token acquired")
        return self._token

    async def ensure_token(self) -> str:
        """Ensure token is available."""
        if self._token:
            return self._token
        return await self.authenticate()

    def clear_token(self) -> None:
        """Clear cached token."""
        self._token = None
