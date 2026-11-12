"""Media files and thumbnails, passed through Home Assistant.

The browser only ever talks to Home Assistant (signed in, or with a signed link); the Kitlig device
token stays on the server. Byte ranges are passed along so video can seek.
"""

from __future__ import annotations

from aiohttp import web
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.config_entries import ConfigEntryState

from .api import KitligError
from .const import DOMAIN

PASS_HEADERS = (
    "Content-Type",
    "Content-Length",
    "Content-Range",
    "Accept-Ranges",
    "ETag",
    "Last-Modified",
    "Content-Disposition",
)


class KitligAssetView(HomeAssistantView):
    """GET /api/kitlig/<entry_id>/asset/<asset_id>/<file|thumb>[/<name>]."""

    url = "/api/kitlig/{entry_id}/asset/{asset_id}/{what}"
    extra_urls = ["/api/kitlig/{entry_id}/asset/{asset_id}/{what}/{name}"]
    name = "api:kitlig:asset"

    async def get(
        self,
        request: web.Request,
        entry_id: str,
        asset_id: str,
        what: str,
        name: str | None = None,
    ) -> web.StreamResponse:
        if what not in ("file", "thumb"):
            raise web.HTTPNotFound
        hass = request.app[KEY_HASS]
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
            raise web.HTTPNotFound
        client = entry.runtime_data.client
        try:
            upstream = await client.open_asset(
                asset_id,
                what,
                range_header=request.headers.get("Range"),
                size=request.query.get("size") if what == "thumb" else None,
            )
        except KitligError as err:
            raise web.HTTPBadGateway(text=str(err)) from err

        try:
            if upstream.status >= 400:
                raise web.HTTPNotFound if upstream.status == 404 else web.HTTPBadGateway
            response = web.StreamResponse(status=upstream.status)
            for header in PASS_HEADERS:
                if header in upstream.headers:
                    response.headers[header] = upstream.headers[header]
            response.headers["Cache-Control"] = (
                "private, max-age=3600" if what == "thumb" else "private, no-cache"
            )
            await response.prepare(request)
            try:
                async for chunk in upstream.content.iter_chunked(64 * 1024):
                    await response.write(chunk)
                await response.write_eof()
            except (ConnectionResetError, ConnectionError):
                pass  # the viewer went away (a seek, a closed tab)
            return response
        finally:
            upstream.release()
