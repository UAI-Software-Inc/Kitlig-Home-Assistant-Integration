"""Buttons: stop what is running, run the last failed job again."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import KitligError
from .const import DOMAIN
from .coordinator import KitligConfigEntry
from .entity import KitligEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KitligConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    if coordinator.read_only:
        return  # KITLIG_WEB_READ_ONLY: the instance refuses job control
    async_add_entities(
        [
            KitligCancelJobs(coordinator, "cancel_running_jobs"),
            KitligRetryFailed(coordinator, "retry_last_failed_job"),
        ]
    )


class KitligCancelJobs(KitligEntity, ButtonEntity):
    async def async_press(self) -> None:
        data = self.coordinator.data
        errors: list[str] = []
        for job in [*data.active_jobs, *data.queued_jobs]:
            try:
                await self.coordinator.cancel_job(job["jobId"])
            except KitligError as err:
                errors.append(str(err))
        if errors:
            raise HomeAssistantError("; ".join(errors))


class KitligRetryFailed(KitligEntity, ButtonEntity):
    async def async_press(self) -> None:
        failed = self.coordinator.data.failed_jobs
        if not failed:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="no_failed_job"
            )
        try:
            await self.coordinator.retry_job(failed[0]["jobId"])
        except KitligError as err:
            raise HomeAssistantError(str(err)) from err
