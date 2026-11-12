"""Binary sensors: is the instance reachable, is it working, is a job waiting for an answer."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import KitligConfigEntry, job_summary
from .entity import KitligEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KitligConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            KitligConnected(coordinator, "connected"),
            KitligWorking(coordinator, "working"),
            KitligNeedsAnswer(coordinator, "needs_answer"),
        ]
    )


class KitligConnected(KitligEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"live_updates": self.coordinator.stream_connected}


class KitligWorking(KitligEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.active_jobs)


class KitligNeedsAnswer(KitligEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.waiting_jobs)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"jobs": [job_summary(j) for j in self.coordinator.data.waiting_jobs[:25]]}
