"""A small stand-in for Kitlig Web, speaking the same routes the integration uses."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from aiohttp import web

PASSWORD = "open-sesame"
FILE_BYTES = bytes(range(256)) * 4  # 1024 bytes
THUMB_BYTES = b"RIFFfakeWEBP"


def job(job_id: str, status: str, label: str, pct: float | None = None) -> dict[str, Any]:
    return {
        "jobId": job_id,
        "status": status,
        "label": label,
        "createdAt": f"2026-11-12T10:00:0{job_id[-1]}.000Z",
        "updatedAt": "2026-11-12T10:00:30.000Z",
        "progress": None if pct is None else {"phase": "render", "pct": pct, "message": "Rendering"},
        "outputs": [],
    }


def asset(asset_id: str, name: str, kind: str, section: str) -> dict[str, Any]:
    return {
        "assetId": asset_id,
        "name": name,
        "kind": kind,
        "section": section,
        "origin": "generated",
        "createdAt": "2026-11-12T09:00:00.000Z",
        "hasThumb": kind in ("image", "video"),
        "revision": 0,
        "editable": False,
    }


class FakeKitlig:
    """Mutable state plus the aiohttp app that serves it."""

    def __init__(self, name: str = "Studio", server_id: str | None = "srv_1") -> None:
        self.name = name
        self.server_id = server_id
        self.web_on = True
        self.read_only = False
        self.project: dict[str, Any] | None = {"projectId": "proj_1", "name": "Launch Film"}
        self.tokens: set[str] = set()
        self.logins = 0
        self.jobs: list[dict[str, Any]] = [
            job("job_2", "running", "Image to Video", 0.5),
            job("job_1", "queued", "Upscale"),
            job("job_0", "failed", "Text to Speech"),
        ]
        self.assets: list[dict[str, Any]] = [
            asset("asset_img", "hero.png", "image", "images"),
            asset("asset_vid", "teaser.mp4", "video", "videos"),
            asset("asset_exp", "Main Cut.mp4", "video", "exports"),
            asset("asset_txt", "notes.md", "text", "text"),
        ]
        self.sites: list[dict[str, Any]] = [
            {
                "siteId": "site_a",
                "name": "Landing Page",
                "kind": "site",
                "slug": "landing",
                "updatedAt": "2026-11-11T10:00:00.000Z",
                "pages": [{"id": "p1", "name": "Home", "file": "index.html"}],
            },
            {
                "siteId": "site_g",
                "name": "Boltway",
                "kind": "game",
                "slug": "boltway",
                "updatedAt": "2026-11-10T10:00:00.000Z",
                "pages": [
                    {"id": "scene.json", "name": "Main (start)", "file": "index.html?scene=scene.json"}
                ],
                "description": "A platformer",
            },
        ]
        self.sequences: list[dict[str, Any]] = [
            {
                "sequenceId": "seq_1",
                "name": "Main Cut",
                "updatedAt": "2026-11-12T08:00:00.000Z",
                "openComments": 3,
                "export": self.assets[2],
                "matchesTimeline": True,
                "votes": {
                    "favorites": 2,
                    "ratingCount": 3,
                    "ratingAverage": 4.5,
                    "mine": {"favorite": False, "rating": 0},
                },
            },
            {
                "sequenceId": "seq_2",
                "name": "Teaser",
                "updatedAt": "2026-11-12T08:00:00.000Z",
                "openComments": 1,
                "export": None,
                "matchesTimeline": False,
                "votes": None,
            },
        ]
        self.has_spend = True
        self.spend_usd = 12.3456
        self.cancelled: list[str] = []
        self.retried: list[str] = []
        self.ranges: list[str | None] = []
        self._streams: list[asyncio.Queue[dict[str, Any] | None]] = []

    # --- Test controls ---------------------------------------------------------------------

    @property
    def stream_count(self) -> int:
        return len(self._streams)

    def push(self, event: dict[str, Any]) -> None:
        for queue in self._streams:
            queue.put_nowait(event)

    def set_job(self, job_id: str, status: str, **extra: Any) -> dict[str, Any]:
        found = next(j for j in self.jobs if j["jobId"] == job_id)
        found.update(status=status, **extra)
        self.push({"type": "job", "job": found})
        return found

    def close_streams(self) -> None:
        for queue in self._streams:
            queue.put_nowait(None)

    # --- The app ---------------------------------------------------------------------------

    def me(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "version": "0.14.0",
            "serverName": self.name,
            "readOnly": self.read_only,
            "activated": True,
            "project": self.project,
            "device": {"id": "dev_1", "name": "Home Assistant"},
            "connected": {"count": len(self.tokens), "max": 10},
        }
        if self.server_id:
            body["serverId"] = self.server_id
        return body

    def app(self) -> web.Application:
        app = web.Application(middlewares=[self._guard])
        add = app.router
        add.add_post("/api/login", self._login)
        add.add_post("/api/logout", self._logout)
        add.add_get("/api/me", self._me)
        add.add_get("/api/jobs", self._jobs)
        add.add_post("/api/jobs/{id}/cancel", self._cancel)
        add.add_post("/api/jobs/{id}/retry", self._retry)
        add.add_get("/api/assets", self._assets)
        add.add_get("/api/assets/{id}", self._asset)
        add.add_get("/api/assets/{id}/thumb", self._thumb)
        add.add_get("/api/assets/{id}/file", self._file)
        add.add_get("/api/sites", self._sites)
        add.add_get("/api/sites/{id}/view", self._view)
        add.add_get("/api/review/sequences", self._sequences)
        add.add_get("/api/events", self._events)
        add.add_get("/api/spend", self._spend)
        return app

    @web.middleware
    async def _guard(self, request: web.Request, handler: Any) -> web.StreamResponse:
        if not self.web_on:
            return web.json_response(
                {
                    "error": "not_found",
                    "message": "Kitlig Web is off. Turn on Phone companion in Settings ▸ MCP Server.",
                },
                status=404,
            )
        if request.method != "GET" and request.headers.get("x-kitlig-web") != "1":
            return web.json_response({"error": "forbidden", "message": "Missing header."}, status=403)
        if request.path != "/api/login":
            token = request.headers.get("Authorization", "").removeprefix("Bearer ")
            if token not in self.tokens:
                return web.json_response({"error": "unauthorized", "message": "Sign in."}, status=401)
        return await handler(request)

    async def _login(self, request: web.Request) -> web.Response:
        body = await request.json()
        if body.get("password") != PASSWORD:
            return web.json_response({"error": "bad_password", "message": "Wrong password."}, status=401)
        if len(self.tokens) >= 10:
            return web.json_response({"error": "device_cap", "message": "Too many devices."}, status=409)
        self.logins += 1
        token = f"tok_{self.name}_{self.logins}"
        self.tokens.add(token)
        return web.json_response({**self.me(), "token": token, "expiresAt": "2026-12-12T00:00:00.000Z"})

    async def _logout(self, request: web.Request) -> web.Response:
        self.tokens.discard(request.headers.get("Authorization", "").removeprefix("Bearer "))
        return web.json_response({"ok": True})

    async def _me(self, request: web.Request) -> web.Response:
        return web.json_response(self.me())

    def _need_project(self) -> web.Response | None:
        if self.project is None:
            return web.json_response({"error": "no_project", "message": "No project is open."}, status=409)
        return None

    async def _jobs(self, request: web.Request) -> web.Response:
        return self._need_project() or web.json_response(self.jobs)

    async def _cancel(self, request: web.Request) -> web.Response:
        job_id = request.match_info["id"]
        self.cancelled.append(job_id)
        found = next(j for j in self.jobs if j["jobId"] == job_id)
        found["status"] = "cancelled"
        return web.json_response(found)

    async def _retry(self, request: web.Request) -> web.Response:
        job_id = request.match_info["id"]
        self.retried.append(job_id)
        found = next(j for j in self.jobs if j["jobId"] == job_id)
        found["status"] = "queued"
        return web.json_response(found, status=202)

    async def _assets(self, request: web.Request) -> web.Response:
        if (missing := self._need_project()) is not None:
            return missing
        section = request.query.get("section", "recent")
        items = [a for a in self.assets if section == "recent" or a["section"] == section]
        return web.json_response({"items": items, "total": len(items)})

    async def _asset(self, request: web.Request) -> web.Response:
        found = next((a for a in self.assets if a["assetId"] == request.match_info["id"]), None)
        if found is None:
            return web.json_response({"error": "not_found", "message": "No such file."}, status=404)
        return web.json_response(found)

    async def _thumb(self, request: web.Request) -> web.Response:
        return web.Response(body=THUMB_BYTES, content_type="image/webp")

    async def _file(self, request: web.Request) -> web.Response:
        header = request.headers.get("Range")
        self.ranges.append(header)
        if header:
            start, end = header.removeprefix("bytes=").split("-")
            lo, hi = int(start), int(end) if end else len(FILE_BYTES) - 1
            return web.Response(
                status=206,
                body=FILE_BYTES[lo : hi + 1],
                content_type="video/mp4",
                headers={"Content-Range": f"bytes {lo}-{hi}/{len(FILE_BYTES)}", "Accept-Ranges": "bytes"},
            )
        return web.Response(body=FILE_BYTES, content_type="video/mp4", headers={"Accept-Ranges": "bytes"})

    async def _sites(self, request: web.Request) -> web.Response:
        return web.json_response({"sites": self.sites if self.project else []})

    async def _view(self, request: web.Request) -> web.Response:
        site = next((s for s in self.sites if s["siteId"] == request.match_info["id"]), None)
        if site is None:
            return web.json_response({"error": "not_found", "message": "No such site or game."}, status=404)
        return web.json_response(
            {
                "url": f"http://{request.host}/view/viewtoken/{site['slug']}/",
                "expiresAt": "2026-11-12T22:00:00.000Z",
            }
        )

    async def _sequences(self, request: web.Request) -> web.Response:
        return self._need_project() or web.json_response({"items": self.sequences})

    async def _spend(self, request: web.Request) -> web.Response:
        if not self.has_spend:  # a Kitlig build from before the route existed
            return web.json_response({"error": "not_found", "message": "Not found."}, status=404)
        if (missing := self._need_project()) is not None:
            return missing

        def totals(usd: float) -> dict[str, Any]:
            return {"usd": usd, "priced": 40, "unpriced": 2, "assumed": 3}

        return web.json_response(
            {
                "currency": "USD",
                "periods": {
                    "lifetime": totals(self.spend_usd),
                    "year": totals(self.spend_usd),
                    "month": totals(4.5),
                    "week": totals(1.25),
                    "day": totals(0.5),
                },
            }
        )

    async def _events(self, request: web.Request) -> web.StreamResponse:
        response = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await response.prepare(request)
        await response.write(b": ping\n\n")
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        self._streams.append(queue)
        try:
            while (event := await queue.get()) is not None:
                await response.write(f"data: {json.dumps(event)}\n\n".encode())
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            self._streams.remove(queue)
        return response
