"""Browse a Kitlig instance's media and exports in Home Assistant's media browser.

Identifiers: `<entry_id>` (an instance), `<entry_id>/<section>` (a list), and
`<entry_id>/<section>/<asset_id>` (a file).
"""

from __future__ import annotations

import mimetypes
from datetime import timedelta
from typing import Any
from urllib.parse import quote

from homeassistant.components.http.auth import async_sign_path
from homeassistant.components.media_player import BrowseError, MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .api import KitligError, KitligNoProjectError
from .const import DOMAIN, MEDIA_MAX_ITEMS, MEDIA_PAGE_SIZE, MEDIA_SECTIONS
from .coordinator import KitligCoordinator

THUMB_LIFETIME = timedelta(hours=6)

KIND_CLASS = {
    "video": (MediaClass.VIDEO, MediaType.VIDEO, "video/mp4"),
    "image": (MediaClass.IMAGE, MediaType.IMAGE, "image/png"),
    "audio": (MediaClass.MUSIC, MediaType.MUSIC, "audio/mpeg"),
}
SECTION_CLASS = {
    "videos": MediaClass.VIDEO,
    "images": MediaClass.IMAGE,
    "audio": MediaClass.MUSIC,
    "exports": MediaClass.VIDEO,
}


async def async_get_media_source(hass: HomeAssistant) -> KitligMediaSource:
    return KitligMediaSource(hass)


def _mime(asset: dict[str, Any]) -> str:
    guessed, _ = mimetypes.guess_type(asset.get("name") or "")
    if guessed:
        return guessed
    return KIND_CLASS.get(asset.get("kind", ""), (None, None, "application/octet-stream"))[2]


class KitligMediaSource(MediaSource):
    name = "Kitlig"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    def _coordinators(self) -> list[KitligCoordinator]:
        return [
            entry.runtime_data
            for entry in self.hass.config_entries.async_entries(DOMAIN)
            if entry.state is ConfigEntryState.LOADED
        ]

    def _coordinator(self, entry_id: str) -> KitligCoordinator:
        for coordinator in self._coordinators():
            if coordinator.config_entry.entry_id == entry_id:
                return coordinator
        raise BrowseError("That Kitlig instance is not connected.")

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        parts = (item.identifier or "").split("/")
        if len(parts) != 3:
            raise Unresolvable("Pick a file to play.")
        entry_id, _section, asset_id = parts
        try:
            coordinator = self._coordinator(entry_id)
            asset = await coordinator.client.asset(asset_id)
        except (BrowseError, KitligError) as err:
            raise Unresolvable(str(err)) from err
        name = quote(asset.get("name") or asset_id, safe="")
        return PlayMedia(f"/api/kitlig/{entry_id}/asset/{asset_id}/file/{name}", _mime(asset))

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        parts = [p for p in (item.identifier or "").split("/") if p]
        if not parts:
            return self._root()
        coordinator = self._coordinator(parts[0])
        if len(parts) == 1:
            return self._instance(coordinator, with_children=True)
        if parts[1] not in MEDIA_SECTIONS:
            raise BrowseError("Unknown section.")
        return await self._section(coordinator, parts[1])

    def _root(self) -> BrowseMediaSource:
        coordinators = self._coordinators()
        root = BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title="Kitlig",
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.DIRECTORY,
        )
        if len(coordinators) == 1:
            # One instance: skip the level that would only hold it.
            root.children = self._instance(coordinators[0], with_children=True).children
        else:
            root.children = [self._instance(c, with_children=False) for c in coordinators]
        return root

    def _instance(self, coordinator: KitligCoordinator, *, with_children: bool) -> BrowseMediaSource:
        entry_id = coordinator.config_entry.entry_id
        project = (coordinator.data.project or {}).get("name")
        title = coordinator.config_entry.title
        node = BrowseMediaSource(
            domain=DOMAIN,
            identifier=entry_id,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title=f"{title} ({project})" if project else title,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.DIRECTORY,
        )
        if with_children:
            node.children = [
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=f"{entry_id}/{section}",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.VIDEO,
                    title=label,
                    can_play=False,
                    can_expand=True,
                    children_media_class=SECTION_CLASS.get(section, MediaClass.VIDEO),
                )
                for section, label in MEDIA_SECTIONS.items()
            ]
        return node

    async def _section(self, coordinator: KitligCoordinator, section: str) -> BrowseMediaSource:
        entry_id = coordinator.config_entry.entry_id
        items: list[dict[str, Any]] = []
        cursor: str | None = None
        try:
            while len(items) < MEDIA_MAX_ITEMS:
                page = await coordinator.client.assets(
                    section, limit=MEDIA_PAGE_SIZE, cursor=cursor
                )
                items.extend(page.get("items", []))
                cursor = page.get("nextCursor")
                if not cursor:
                    break
        except KitligNoProjectError:
            items = []
        except KitligError as err:
            raise BrowseError(str(err)) from err

        children: list[BrowseMediaSource] = []
        for asset in items:
            kind = KIND_CLASS.get(asset.get("kind", ""))
            if kind is None:
                continue  # text, zips and other files the media browser cannot show
            media_class, _, _ = kind
            thumbnail = None
            if asset.get("hasThumb"):
                thumbnail = async_sign_path(
                    self.hass,
                    f"/api/kitlig/{entry_id}/asset/{asset['assetId']}/thumb",
                    THUMB_LIFETIME,
                )
            children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=f"{entry_id}/{section}/{asset['assetId']}",
                    media_class=media_class,
                    media_content_type=_mime(asset),
                    title=asset.get("name") or asset["assetId"],
                    can_play=True,
                    can_expand=False,
                    thumbnail=thumbnail,
                )
            )
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{entry_id}/{section}",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title=MEDIA_SECTIONS[section],
            can_play=False,
            can_expand=True,
            children=children,
            children_media_class=SECTION_CLASS.get(section, MediaClass.VIDEO),
        )
