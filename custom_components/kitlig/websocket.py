"""Data for the Kitlig dashboard card."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .api import KitligError
from .const import DOMAIN
from .coordinator import KitligCoordinator, job_summary


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_instances)
    websocket_api.async_register_command(hass, ws_site_url)


def _instance(coordinator: KitligCoordinator) -> dict[str, Any]:
    data = coordinator.data
    return {
        "entry_id": coordinator.config_entry.entry_id,
        "name": coordinator.config_entry.title,
        "connected": coordinator.last_update_success,
        "project": (data.project or {}).get("name"),
        "jobs_running": len(data.active_jobs),
        "jobs_queued": len(data.queued_jobs),
        "current_job": job_summary(data.current_job) if data.current_job else None,
        "sites": [
            {
                "site_id": s.get("siteId"),
                "name": s.get("name"),
                "kind": s.get("kind"),
                "updated": s.get("updatedAt"),
                "description": s.get("description"),
                "icon": s.get("icon"),
                "pages": [
                    {"name": p.get("name"), "file": p.get("file")} for p in s.get("pages") or []
                ],
            }
            for s in data.sites
        ],
    }


@websocket_api.websocket_command(
    {vol.Required("type"): "kitlig/instances", vol.Optional("entry_id"): str}
)
@callback
def ws_instances(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Every loaded instance (or one), with its sites and games."""
    wanted = msg.get("entry_id")
    instances = [
        _instance(entry.runtime_data)
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED and wanted in (None, entry.entry_id)
    ]
    connection.send_result(msg["id"], {"instances": instances})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "kitlig/site_url",
        vol.Required("entry_id"): str,
        vol.Required("site_id"): str,
        vol.Optional("page"): str,
    }
)
@websocket_api.async_response
async def ws_site_url(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """A fresh link that opens a site or game."""
    from . import async_get_coordinator

    try:
        coordinator = async_get_coordinator(hass, msg["entry_id"])
        result = await coordinator.site_url(msg["site_id"], msg.get("page"))
    except (KitligError, HomeAssistantError) as err:
        connection.send_error(msg["id"], "kitlig_error", str(err))
        return
    connection.send_result(msg["id"], result)
