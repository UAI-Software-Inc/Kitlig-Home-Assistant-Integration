"""Client for Kitlig Web, the REST and server-sent-events API a Kitlig instance serves.

The contract is docs/api/kitlig-web.openapi.yaml in the Kitlig repository. Everything here is by
id: no file path ever crosses the API.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import aiohttp

WRITE_HEADER = {"x-kitlig-web": "1"}
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)
# The stream sends a ping every 25 s; a minute of silence means the connection is dead.
STREAM_TIMEOUT = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=60)
PROXY_TIMEOUT = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=60)


class KitligError(Exception):
    """Any failure talking to Kitlig."""

    def __init__(self, message: str, code: str | None = None, status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


class KitligConnectionError(KitligError):
    """The instance could not be reached."""


class KitligAuthError(KitligError):
    """The password or device token was refused."""


class KitligWebOffError(KitligError):
    """The server answers, but Kitlig Web (Phone companion) is switched off."""


class KitligDeviceCapError(KitligError):
    """The instance already has its maximum number of signed-in devices."""


class KitligRateLimitError(KitligError):
    """Too many sign-in attempts."""


class KitligNoProjectError(KitligError):
    """No project is open on the instance."""


class KitligClient:
    """One Kitlig instance."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        token: str | None = None,
    ) -> None:
        self._session = session
        self.host = host
        self.port = port
        self.token = token

    @property
    def base_url(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"http://{host}:{self.port}"

    def _auth(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> Any:
        headers = dict(self._auth()) if auth else {}
        if method != "GET":
            headers.update(WRITE_HEADER)
        try:
            async with self._session.request(
                method,
                f"{self.base_url}{path}",
                params=params,
                json=body,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status < 300:
                    return await resp.json(content_type=None)
                raise await _error_from(resp)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise KitligConnectionError(f"Cannot reach Kitlig at {self.base_url}: {err}") from err

    # --- Sign-in ---------------------------------------------------------------------------

    async def login(self, password: str, device_name: str) -> dict[str, Any]:
        """Trade the password for a device token. Stores the token on this client."""
        result = await self._request(
            "POST",
            "/api/login",
            body={"password": password, "deviceName": device_name},
            auth=False,
        )
        self.token = result["token"]
        return result

    async def logout(self) -> None:
        await self._request("POST", "/api/logout")

    # --- Reads -----------------------------------------------------------------------------

    async def me(self) -> dict[str, Any]:
        return await self._request("GET", "/api/me")

    async def jobs(self, limit: int = 200) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/jobs", params={"limit": limit})

    async def assets(
        self,
        section: str = "recent",
        *,
        limit: int = 60,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"section": section, "limit": limit, "sort": "newest"}
        if cursor:
            params["cursor"] = cursor
        return await self._request("GET", "/api/assets", params=params)

    async def asset(self, asset_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/assets/{asset_id}")

    async def sites(self) -> list[dict[str, Any]]:
        return (await self._request("GET", "/api/sites")).get("sites", [])

    async def site_view(self, site_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/sites/{site_id}/view")

    async def spend(self) -> dict[str, Any] | None:
        """The open project's estimated spend per period. None on a Kitlig without the route."""
        try:
            return await self._request("GET", "/api/spend")
        except KitligNoProjectError:
            return None
        except KitligError as err:
            if err.status in (404, 405):
                return None
            raise

    async def review_sequences(self) -> list[dict[str, Any]]:
        return (await self._request("GET", "/api/review/sequences")).get("items", [])

    # --- Writes ----------------------------------------------------------------------------

    async def cancel_job(self, job_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/api/jobs/{job_id}/cancel")

    async def retry_job(self, job_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/api/jobs/{job_id}/retry")

    # --- Bytes -----------------------------------------------------------------------------

    async def fetch_thumb(self, asset_id: str, size: str = "grid") -> tuple[bytes, str]:
        """A thumbnail's bytes and content type."""
        try:
            async with self._session.get(
                f"{self.base_url}/api/assets/{asset_id}/thumb",
                params={"size": size},
                headers=self._auth(),
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status >= 300:
                    raise await _error_from(resp)
                return await resp.read(), resp.content_type or "image/webp"
        except (TimeoutError, aiohttp.ClientError) as err:
            raise KitligConnectionError(f"Cannot reach Kitlig at {self.base_url}: {err}") from err

    async def open_asset(
        self, asset_id: str, what: str, *, range_header: str | None = None, size: str | None = None
    ) -> aiohttp.ClientResponse:
        """Open a file or thumbnail response for streaming. The caller releases it."""
        headers = dict(self._auth())
        if range_header:
            headers["Range"] = range_header
        params = {"size": size} if size else None
        try:
            return await self._session.get(
                f"{self.base_url}/api/assets/{asset_id}/{what}",
                params=params,
                headers=headers,
                timeout=PROXY_TIMEOUT,
            )
        except (TimeoutError, aiohttp.ClientError) as err:
            raise KitligConnectionError(f"Cannot reach Kitlig at {self.base_url}: {err}") from err

    # --- Live events -----------------------------------------------------------------------

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        """Yield Kitlig Web events until the stream ends. Raises when it breaks."""
        try:
            async with self._session.get(
                f"{self.base_url}/api/events",
                headers={**self._auth(), "Accept": "text/event-stream"},
                timeout=STREAM_TIMEOUT,
            ) as resp:
                if resp.status >= 300:
                    raise await _error_from(resp)
                data: list[str] = []
                async for raw in resp.content:
                    line = raw.decode("utf-8", "replace").rstrip("\r\n")
                    if line.startswith("data:"):
                        data.append(line[5:].lstrip())
                        continue
                    if line or not data:
                        continue  # a comment (": ping"), another field, or a stray blank line
                    payload, data = "\n".join(data), []
                    try:
                        event = json.loads(payload)
                    except ValueError:
                        continue
                    if isinstance(event, dict):
                        yield event
        except (TimeoutError, aiohttp.ClientError) as err:
            raise KitligConnectionError(f"Event stream from {self.base_url} broke: {err}") from err


async def _error_from(resp: aiohttp.ClientResponse) -> KitligError:
    code: str | None = None
    message = f"Kitlig answered {resp.status}"
    try:
        payload = await resp.json(content_type=None)
        if isinstance(payload, dict):
            code = payload.get("error")
            message = payload.get("message") or message
    except (ValueError, aiohttp.ClientError):
        pass
    status = resp.status
    if status == 401:
        return KitligAuthError(message, code, status)
    if status == 404 and code == "not_found" and "Kitlig Web is off" in message:
        return KitligWebOffError(message, code, status)
    if code == "device_cap":
        return KitligDeviceCapError(message, code, status)
    if status == 429:
        return KitligRateLimitError(message, code, status)
    if code == "no_project":
        return KitligNoProjectError(message, code, status)
    return KitligError(message, code, status)
