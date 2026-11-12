"""Keeps one Kitlig instance's state current: live events first, a slow poll as the safety net."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field, replace
from datetime import timedelta
from time import monotonic
from typing import Any
from urllib.parse import urlsplit

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, CONF_TOKEN
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import KitligAuthError, KitligClient, KitligError, KitligNoProjectError
from .const import (
    ACTIVE_STATUSES,
    CONF_BROWSER_URL,
    CONF_READ_ONLY,
    DEFAULT_SCAN_INTERVAL,
    EVENT_JOB,
    SIGNAL_JOB_EVENT,
    SLOW_REFRESH_SECONDS,
    STATUS_AWAITING_INPUT,
    STATUS_FAILED,
    STATUS_QUEUED,
    STATUS_TO_EVENT,
)

_LOGGER = logging.getLogger(__name__)

type KitligConfigEntry = ConfigEntry[KitligCoordinator]

SLICES = frozenset({"sites", "review", "assets", "spend"})
# A job first seen already finished only counts as news when it finished this recently.
FRESH_SECONDS = 180


@dataclass(frozen=True)
class KitligData:
    """What one instance looks like right now."""

    me: dict[str, Any] = field(default_factory=dict)
    jobs: dict[str, dict[str, Any]] = field(default_factory=dict)
    sites: list[dict[str, Any]] = field(default_factory=list)
    sequences: list[dict[str, Any]] = field(default_factory=list)
    latest: dict[str, Any] | None = None
    spend: dict[str, Any] | None = None

    @property
    def project(self) -> dict[str, Any] | None:
        return self.me.get("project")

    def _sorted(self, statuses: frozenset[str] | set[str]) -> list[dict[str, Any]]:
        jobs = [j for j in self.jobs.values() if j.get("status") in statuses]
        return sorted(jobs, key=lambda j: j.get("createdAt", ""), reverse=True)

    @property
    def active_jobs(self) -> list[dict[str, Any]]:
        return self._sorted(ACTIVE_STATUSES)

    @property
    def queued_jobs(self) -> list[dict[str, Any]]:
        return self._sorted({STATUS_QUEUED})

    @property
    def waiting_jobs(self) -> list[dict[str, Any]]:
        return self._sorted({STATUS_AWAITING_INPUT})

    @property
    def failed_jobs(self) -> list[dict[str, Any]]:
        jobs = [j for j in self.jobs.values() if j.get("status") == STATUS_FAILED]
        return sorted(jobs, key=lambda j: j.get("updatedAt", ""), reverse=True)

    @property
    def current_job(self) -> dict[str, Any] | None:
        active = self.active_jobs
        return active[0] if active else None

    @property
    def open_comments(self) -> int:
        return sum(int(s.get("openComments") or 0) for s in self.sequences)


def job_progress(job: dict[str, Any] | None) -> int | None:
    """A job's progress as a whole percent, when it reports one."""
    pct = ((job or {}).get("progress") or {}).get("pct")
    return None if pct is None else max(0, min(100, round(float(pct) * 100)))


def job_summary(job: dict[str, Any]) -> dict[str, Any]:
    progress = job.get("progress") or {}
    return {
        "job_id": job.get("jobId"),
        "label": job.get("label"),
        "status": job.get("status"),
        "progress": job_progress(job),
        "phase": progress.get("phase"),
        "message": progress.get("message"),
        "started": job.get("createdAt"),
    }


class KitligCoordinator(DataUpdateCoordinator[KitligData]):
    """One per config entry, so one per Kitlig instance."""

    config_entry: KitligConfigEntry

    def __init__(self, hass: HomeAssistant, entry: KitligConfigEntry) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"Kitlig {entry.title}",
            update_interval=timedelta(seconds=interval),
        )
        self.client = KitligClient(
            async_get_clientsession(hass),
            entry.data[CONF_HOST],
            entry.data[CONF_PORT],
            entry.data[CONF_TOKEN],
        )
        self.data = KitligData()
        self.stream_connected = False
        self._dirty: set[str] = set(SLICES)
        self._slow_at = 0.0
        self._statuses: dict[str, str] = {}
        self._primed = False
        self._epoch = 0

    @property
    def read_only(self) -> bool:
        return bool(self.data.me.get("readOnly", self.config_entry.data.get(CONF_READ_ONLY)))

    # --- Polling ---------------------------------------------------------------------------

    async def _async_update_data(self) -> KitligData:
        # An event that lands while a fetch is in flight is newer than what the fetch read, so the
        # fetch is thrown away and run again rather than written over the event.
        for _ in range(3):
            epoch = self._epoch
            data, fetched = await self._fetch()
            if epoch == self._epoch:
                break
            self._dirty |= fetched

        for job in data.jobs.values():
            self._note_job(job)
        self._statuses = {k: v for k, v in self._statuses.items() if k in data.jobs}
        self._primed = True
        return data

    async def _fetch(self) -> tuple[KitligData, set[str]]:
        """Read the instance. Returns the new state and which slow slices it re-read."""
        try:
            me = await self.client.me()
            has_project = me.get("project") is not None
            jobs = await self._or_empty(self.client.jobs()) if has_project else []
            # A different project (or the first one since Kitlig started) makes everything stale,
            # whether or not the event stream was connected to say so.
            if (me.get("project") or {}).get("projectId") != (self.data.project or {}).get(
                "projectId"
            ) or monotonic() - self._slow_at > SLOW_REFRESH_SECONDS:
                self._dirty = set(SLICES)
            dirty, self._dirty = self._dirty, set()
            data = replace(self.data, me=me, jobs={j["jobId"]: j for j in jobs})
            if "sites" in dirty:
                data = replace(
                    data, sites=await self._or_empty(self.client.sites()) if has_project else []
                )
            if "review" in dirty:
                data = replace(
                    data,
                    sequences=await self._or_empty(self.client.review_sequences())
                    if has_project
                    else [],
                )
            if "assets" in dirty:
                data = replace(data, latest=await self._latest() if has_project else None)
            if "spend" in dirty:
                data = replace(data, spend=await self.client.spend() if has_project else None)
            if dirty == SLICES:
                self._slow_at = monotonic()
        except KitligAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except KitligError as err:
            self._dirty = set(SLICES)
            raise UpdateFailed(str(err)) from err
        return data, dirty

    @staticmethod
    async def _or_empty(call: Any) -> list[dict[str, Any]]:
        """A list call that reads as empty when the project was closed underneath it."""
        try:
            return await call
        except KitligNoProjectError:
            return []

    async def _latest(self) -> dict[str, Any] | None:
        try:
            page = await self.client.assets("recent", limit=12)
        except KitligNoProjectError:
            return None
        return next((a for a in page.get("items", []) if a.get("hasThumb")), None)

    # --- Live events -----------------------------------------------------------------------

    async def listen(self) -> None:
        """Follow the instance's event stream for as long as the entry is loaded."""
        backoff = 5
        while True:
            try:
                async for event in self.client.events():
                    if not self.stream_connected:
                        self.stream_connected = True
                        backoff = 5
                        # Whatever happened while the stream was down was missed.
                        self._refresh(set(SLICES))
                    self._handle_event(event)
            except KitligAuthError:
                self.stream_connected = False
                await self.async_request_refresh()  # the poll raises the reauth request
                return
            except KitligError as err:
                _LOGGER.debug("Kitlig event stream for %s: %s", self.config_entry.title, err)
            self.stream_connected = False
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

    @callback
    def _handle_event(self, event: dict[str, Any]) -> None:
        kind = event.get("type")
        self._epoch += 1
        if kind == "job" and isinstance(event.get("job"), dict):
            job = event["job"]
            self._note_job(job)
            self.async_set_updated_data(
                replace(self.data, jobs={**self.data.jobs, job["jobId"]: job})
            )
            if job.get("status") == "complete":
                self._refresh({"assets", "spend"})
            return
        if kind == "project":
            self.async_set_updated_data(
                replace(self.data, me={**self.data.me, "project": event.get("project")}, jobs={})
            )
            self._statuses = {}
            self._primed = False
            self._refresh(set(SLICES))
        elif kind == "assets":
            self._refresh({"assets", "review"})
        elif kind == "comments":
            self._refresh({"review"})
        elif kind == "sites":
            self._refresh({"sites"})

    @callback
    def _refresh(self, slices: set[str]) -> None:
        self._dirty |= slices
        self.hass.async_create_task(self.async_request_refresh())

    # --- Job news --------------------------------------------------------------------------

    @callback
    def _note_job(self, job: dict[str, Any]) -> None:
        job_id, status = job.get("jobId"), job.get("status")
        if not job_id or not status:
            return
        before = self._statuses.get(job_id)
        self._statuses[job_id] = status
        if before == status or not self._primed:
            return
        event_type = STATUS_TO_EVENT.get(status)
        if event_type is None:
            return
        if before is None and not _is_fresh(job):
            return
        payload = {
            "type": event_type,
            "job_id": job_id,
            "label": job.get("label"),
            "status": status,
            "error": job.get("error"),
            "outputs": [o.get("assetId") for o in job.get("outputs") or []],
            "instance": self.config_entry.title,
            "project": (self.data.project or {}).get("name"),
        }
        async_dispatcher_send(
            self.hass, SIGNAL_JOB_EVENT.format(self.config_entry.entry_id), event_type, payload
        )
        devices = dr.async_entries_for_config_entry(
            dr.async_get(self.hass), self.config_entry.entry_id
        )
        device = devices[0] if devices else None
        self.hass.bus.async_fire(
            EVENT_JOB,
            {
                **payload,
                "config_entry_id": self.config_entry.entry_id,
                "device_id": device.id if device else None,
            },
        )

    # --- Actions ---------------------------------------------------------------------------

    async def cancel_job(self, job_id: str) -> None:
        self._handle_event({"type": "job", "job": await self.client.cancel_job(job_id)})

    async def retry_job(self, job_id: str) -> None:
        self._handle_event({"type": "job", "job": await self.client.retry_job(job_id)})

    async def site_url(self, site_id: str, page: str | None = None) -> dict[str, Any]:
        """A link that opens a site or game in a browser, good until `expires_at`."""
        view = await self.client.site_view(site_id)
        url: str = view["url"]
        browser_url = (self.config_entry.options.get(CONF_BROWSER_URL) or "").strip().rstrip("/")
        if browser_url:
            url = f"{browser_url}{urlsplit(url).path}"
        if page:
            url = f"{url.rstrip('/')}/{page.lstrip('/')}"
        return {"url": url, "expires_at": view.get("expiresAt")}


def _is_fresh(job: dict[str, Any]) -> bool:
    updated = dt_util.parse_datetime(job.get("updatedAt") or "")
    if updated is None:
        return False
    return (dt_util.utcnow() - dt_util.as_utc(updated)).total_seconds() < FRESH_SECONDS
