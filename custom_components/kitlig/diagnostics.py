"""Diagnostics download, with the device token left out."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_TOKEN
from homeassistant.core import HomeAssistant

from .coordinator import KitligConfigEntry, job_summary

TO_REDACT = {CONF_TOKEN, "token", "device"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: KitligConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "live_updates": coordinator.stream_connected,
        "last_update_success": coordinator.last_update_success,
        "me": async_redact_data(data.me, TO_REDACT),
        "jobs": [job_summary(j) for j in data.jobs.values()],
        "site_count": len(data.sites),
        "sequence_count": len(data.sequences),
        "latest": data.latest,
        "spend": data.spend,
    }
