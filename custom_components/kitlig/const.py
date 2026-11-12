"""Constants for the Kitlig integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "kitlig"
VERSION: Final = "0.1.0"

DEFAULT_PORT: Final = 8420
DEFAULT_SCAN_INTERVAL: Final = 30
MIN_SCAN_INTERVAL: Final = 10
SLOW_REFRESH_SECONDS: Final = 300

CONF_SERVER_ID: Final = "server_id"
CONF_BROWSER_URL: Final = "browser_url"
CONF_READ_ONLY: Final = "read_only"

DEVICE_NAME: Final = "Home Assistant"

# Job states, as Kitlig Web reports them (src/shared/schemas/job.schema.ts in Kitlig).
STATUS_QUEUED: Final = "queued"
STATUS_AWAITING_INPUT: Final = "awaiting-input"
STATUS_COMPLETE: Final = "complete"
STATUS_FAILED: Final = "failed"
STATUS_CANCELLED: Final = "cancelled"
ACTIVE_STATUSES: Final = frozenset(
    {"running", "uploading", "submitted", "polling", "downloading", "validating"}
)
TERMINAL_STATUSES: Final = frozenset({STATUS_COMPLETE, STATUS_FAILED, STATUS_CANCELLED})

# Bus event and its types (also the event entity's types and the device triggers).
EVENT_JOB: Final = "kitlig_job"
JOB_FINISHED: Final = "finished"
JOB_FAILED: Final = "failed"
JOB_CANCELLED: Final = "cancelled"
JOB_NEEDS_ANSWER: Final = "needs_answer"
JOB_EVENT_TYPES: Final = [JOB_FINISHED, JOB_FAILED, JOB_CANCELLED, JOB_NEEDS_ANSWER]
STATUS_TO_EVENT: Final = {
    STATUS_COMPLETE: JOB_FINISHED,
    STATUS_FAILED: JOB_FAILED,
    STATUS_CANCELLED: JOB_CANCELLED,
    STATUS_AWAITING_INPUT: JOB_NEEDS_ANSWER,
}

SIGNAL_JOB_EVENT: Final = "kitlig_job_event_{}"

# Media browser sections: Kitlig Web's section name -> label.
MEDIA_SECTIONS: Final = {
    "recent": "Recent",
    "videos": "Videos",
    "images": "Images",
    "audio": "Audio",
    "exports": "Exports",
}
MEDIA_PAGE_SIZE: Final = 200
MEDIA_MAX_ITEMS: Final = 600

CARD_URL: Final = "/kitlig_static/kitlig-card.js"

SERVICE_CANCEL_JOB: Final = "cancel_job"
SERVICE_RETRY_JOB: Final = "retry_job"
SERVICE_GET_SITE_URL: Final = "get_site_url"
ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"
ATTR_JOB_ID: Final = "job_id"
ATTR_SITE_ID: Final = "site_id"
ATTR_PAGE: Final = "page"
