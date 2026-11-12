"""An event entity that fires when a job finishes, fails, is cancelled or needs an answer."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import JOB_EVENT_TYPES, SIGNAL_JOB_EVENT
from .coordinator import KitligConfigEntry
from .entity import KitligEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KitligConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([KitligJobEvent(entry.runtime_data, "job")])


class KitligJobEvent(KitligEntity, EventEntity):
    _attr_event_types = JOB_EVENT_TYPES

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_JOB_EVENT.format(self.coordinator.config_entry.entry_id),
                self._on_job,
            )
        )

    @callback
    def _on_job(self, event_type: str, payload: dict[str, Any]) -> None:
        self._trigger_event(event_type, {k: v for k, v in payload.items() if k != "type"})
        self.async_write_ha_state()
