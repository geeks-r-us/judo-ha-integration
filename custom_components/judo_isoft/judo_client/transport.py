"""Transport layer for local and cloud Judo API access."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .auth import CloudAuthenticator
from .models import TransportMode

_LOGGER = logging.getLogger(__name__)


class JudoTransportError(Exception):
    """Raised for transport-level errors."""


class JudoTransport:
    """Low-level transport for local `/api/rest` and cloud interface."""

    CLOUD_BASE_URL = "https://www.myjudo.eu/interface"

    def __init__(
        self,
        host: str,
        port: int,
        timeout: int,
        username: str | None,
        password: str | None,
        force_cloud: bool,
    ) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._username = username
        self._password = password
        self._force_cloud = force_cloud
        self._session: aiohttp.ClientSession | None = None
        self._auth: CloudAuthenticator | None = None

    @property
    def local_base_url(self) -> str:
        """Return local base URL."""
        return f"http://{self._host}:{self._port}"

    async def session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            # Force threaded DNS resolver to avoid environment-specific aiodns/pycares
            # incompatibilities (e.g. Channel.getaddrinfo signature errors).
            connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._timeout),
                connector=connector,
            )
        return self._session

    async def authenticator(self) -> CloudAuthenticator:
        """Get or create cloud authenticator."""
        if self._auth is None:
            self._auth = CloudAuthenticator(
                await self.session(),
                self.CLOUD_BASE_URL,
                self._username,
                self._password,
                self._timeout,
            )
        return self._auth

    async def close(self) -> None:
        """Close transport resources."""
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def request_local(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute local request and return normalized response."""
        session = await self.session()
        url = f"{self.local_base_url}/{path.lstrip('/')}"
        try:
            async with session.request(method, url, params=params, json=json_data) as response:
                text = await response.text()
                response.raise_for_status()
                try:
                    data = await response.json(content_type=None)
                    if isinstance(data, dict):
                        data.setdefault("_source", "local")
                        return data
                    return {"value": data, "raw_text": text, "_source": "local"}
                except Exception:
                    return {"raw_text": text, "_source": "local"}
        except Exception as err:
            raise JudoTransportError(f"Local request failed: {err}") from err

    async def request_cloud(
        self,
        method: str,
        *,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute cloud request and return normalized response."""
        session = await self.session()
        try:
            async with session.request(method, self.CLOUD_BASE_URL, params=params) as response:
                text = await response.text()
                response.raise_for_status()
                try:
                    data = await response.json(content_type=None)
                    if isinstance(data, dict):
                        data.setdefault("_source", "cloud")
                        data.setdefault("raw_text", text)
                        data.setdefault("status_code", response.status)
                        return data
                    return {
                        "value": data,
                        "raw_text": text,
                        "status_code": response.status,
                        "_source": "cloud",
                    }
                except Exception:
                    return {
                        "raw_text": text,
                        "status_code": response.status,
                        "_source": "cloud",
                    }
        except Exception as err:
            raise JudoTransportError(f"Cloud request failed: {err}") from err

    async def read_local_command(self, command_id: int) -> dict[str, Any]:
        """Read one local command using REST command endpoint."""
        path = f"api/rest/{command_id:02X}00"
        return await self.request_local("GET", path)

    async def write_local_command(self, command_id: int, payload_hex: str) -> dict[str, Any]:
        """Write one local command using REST command endpoint."""
        path = f"api/rest/{command_id:02X}00{payload_hex}"
        return await self.request_local("GET", path)

    async def read_cloud_device_data(self) -> dict[str, Any]:
        """Read cloud device data payload."""
        auth = await self.authenticator()
        token = await auth.ensure_token()
        params = {
            "group": "register",
            "command": "get device data",
            "token": token,
        }
        try:
            return await self.request_cloud("GET", params=params)
        except JudoTransportError:
            auth.clear_token()
            token = await auth.ensure_token()
            params["token"] = token
            return await self.request_cloud("GET", params=params)

    async def write_cloud_command(
        self,
        command_id: int,
        payload_hex: str,
        sn: str | None = None,
        serialnumber: str | None = None,
        ewuid: str | None = None,
        cmd_encoding: str = "hex",
    ) -> dict[str, Any]:
        """Write command via cloud interface."""
        auth = await self.authenticator()
        token = await auth.ensure_token()
        normalized_cmd_encoding = str(cmd_encoding).lower()
        if normalized_cmd_encoding == "dec":
            cmd_value = str(int(command_id))
        elif normalized_cmd_encoding == "rest_inline":
            cmd_value = f"{command_id:02X}00{payload_hex}"
        elif normalized_cmd_encoding in {"hex00", "rest"}:
            cmd_value = f"{command_id:02X}00"
        else:
            cmd_value = f"{command_id:02X}"
        params = {
            "group": "register",
            "command": "set device data",
            "token": token,
            "cmd": cmd_value,
        }
        if normalized_cmd_encoding != "rest_inline":
            params["data"] = payload_hex
        resolved_sn = str(sn or "").strip()
        resolved_serial = str(serialnumber or "").strip()
        # Preserve the exact target tuple the caller selected. Some cloud write
        # routes appear to depend on which identifier keys are present.
        if resolved_sn:
            params["sn"] = resolved_sn
        if resolved_serial:
            params["serialnumber"] = resolved_serial
        resolved_ewuid = str(ewuid or "").strip()
        if resolved_ewuid:
            params["ewuid"] = resolved_ewuid
        try:
            return await self.request_cloud("GET", params=params)
        except JudoTransportError:
            auth.clear_token()
            token = await auth.ensure_token()
            params["token"] = token
            return await self.request_cloud("GET", params=params)

    async def best_effort_mode(self) -> TransportMode:
        """Return preferred transport mode."""
        if self._force_cloud:
            return TransportMode.CLOUD
        return TransportMode.AUTO
