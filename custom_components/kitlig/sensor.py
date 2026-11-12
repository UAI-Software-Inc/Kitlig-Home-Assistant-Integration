"""Sensors: job counts, the current job, the open project, review notes, sites and games."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import KitligConfigEntry, KitligCoordinator, KitligData, job_progress, job_summary
from .entity import KitligEntity

MAX_LISTED = 25


@dataclass(frozen=True, kw_only=True)
class KitligSensorDescription(SensorEntityDescription):
    value_fn: Callable[[KitligData], Any]
    attrs_fn: Callable[[KitligData], dict[str, Any]] | None = None


def _jobs_attr(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    return {"jobs": [job_summary(j) for j in jobs[:MAX_LISTED]]}


def _current_attrs(data: KitligData) -> dict[str, Any]:
    job = data.current_job
    if job is None:
        return {}
    summary = job_summary(job)
    summary.pop("label")
    return summary


def _sites_attr(data: KitligData, kind: str) -> dict[str, Any]:
    return {
        "items": [
            {
                "site_id": s.get("siteId"),
                "name": s.get("name"),
                "updated": s.get("updatedAt"),
                "pages": [p.get("name") for p in s.get("pages") or []],
            }
            for s in data.sites
            if s.get("kind") == kind
        ][:MAX_LISTED]
    }


def _review_attrs(data: KitligData) -> dict[str, Any]:
    return {
        "sequences": [
            {
                "name": s.get("name"),
                "open_comments": s.get("openComments"),
                "latest_export": (s.get("export") or {}).get("name"),
                "matches_timeline": s.get("matchesTimeline"),
                "favorites": (s.get("votes") or {}).get("favorites"),
                "rating": (s.get("votes") or {}).get("ratingAverage"),
                "rating_count": (s.get("votes") or {}).get("ratingCount"),
            }
            for s in data.sequences[:MAX_LISTED]
        ]
    }


def _spend_usd(data: KitligData, period: str) -> float | None:
    totals = ((data.spend or {}).get("periods") or {}).get(period)
    return None if totals is None else round(float(totals.get("usd") or 0), 4)


def _spend_attrs(data: KitligData) -> dict[str, Any]:
    if not data.spend:
        return {}
    lifetime = (data.spend.get("periods") or {}).get("lifetime") or {}
    return {
        "today": _spend_usd(data, "day"),
        "this_week": _spend_usd(data, "week"),
        "this_month": _spend_usd(data, "month"),
        "this_year": _spend_usd(data, "year"),
        "priced_runs": lifetime.get("priced"),
        "unpriced_runs": lifetime.get("unpriced"),
        "runs_priced_at_a_default_size": lifetime.get("assumed"),
        "estimate": True,
        "project": (data.project or {}).get("name"),
    }


SENSORS: tuple[KitligSensorDescription, ...] = (
    KitligSensorDescription(
        key="jobs_running",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: len(d.active_jobs),
        attrs_fn=lambda d: _jobs_attr(d.active_jobs),
    ),
    KitligSensorDescription(
        key="jobs_queued",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: len(d.queued_jobs),
        attrs_fn=lambda d: _jobs_attr(d.queued_jobs),
    ),
    KitligSensorDescription(
        key="current_job",
        value_fn=lambda d: (d.current_job or {}).get("label"),
        attrs_fn=_current_attrs,
    ),
    KitligSensorDescription(
        key="current_job_progress",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: job_progress(d.current_job),
    ),
    KitligSensorDescription(
        key="project",
        value_fn=lambda d: (d.project or {}).get("name"),
        attrs_fn=lambda d: {"project_id": (d.project or {}).get("projectId")},
    ),
    KitligSensorDescription(
        key="project_spend",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="USD",
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        value_fn=lambda d: _spend_usd(d, "lifetime"),
        attrs_fn=_spend_attrs,
    ),
    KitligSensorDescription(
        key="open_review_comments",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.open_comments,
        attrs_fn=_review_attrs,
    ),
    KitligSensorDescription(
        key="sites",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: sum(1 for s in d.sites if s.get("kind") == "site"),
        attrs_fn=lambda d: _sites_attr(d, "site"),
    ),
    KitligSensorDescription(
        key="games",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: sum(1 for s in d.sites if s.get("kind") == "game"),
        attrs_fn=lambda d: _sites_attr(d, "game"),
    ),
    KitligSensorDescription(
        key="version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.me.get("version"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KitligConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(KitligSensor(entry.runtime_data, description) for description in SENSORS)


class KitligSensor(KitligEntity, SensorEntity):
    entity_description: KitligSensorDescription

    def __init__(self, coordinator: KitligCoordinator, description: KitligSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        fn = self.entity_description.attrs_fn
        return fn(self.coordinator.data) if fn else None
