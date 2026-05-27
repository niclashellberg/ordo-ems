"""Home Assistant WebSocket client (live state + actuation)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Optional

import aiohttp

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    def __init__(self, base_url: str, token: str):
        self._base = base_url.rstrip("/")
        self._token = token
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._msg_id = 1
        self._states: dict[str, dict[str, Any]] = {}

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def connect(self) -> None:
        self._session = aiohttp.ClientSession(headers=self.headers)
        url = self._base.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{url}/api/websocket"
        self._ws = await self._session.ws_connect(ws_url)
        auth = await self._ws.receive_json()
        if auth.get("type") != "auth_required":
            raise RuntimeError(f"unexpected WS hello: {auth}")
        await self._ws.send_json({"type": "auth", "access_token": self._token})
        ok = await self._ws.receive_json()
        if ok.get("type") != "auth_ok":
            raise RuntimeError(f"HA auth failed: {ok}")
        await self._send({"type": "subscribe_events", "event_type": "state_changed"})
        asyncio.create_task(self._listen())

    async def _send(self, msg: dict) -> int:
        mid = self._msg_id
        self._msg_id += 1
        msg["id"] = mid
        assert self._ws
        await self._ws.send_json(msg)
        return mid

    async def _listen(self) -> None:
        assert self._ws
        async for msg in self._ws:
            if msg.type != aiohttp.WSMsgType.TEXT:
                continue
            data = json.loads(msg.data)
            if data.get("type") == "event":
                ev = data.get("event", {}).get("data", {})
                ent = ev.get("entity_id")
                new = ev.get("new_state")
                if ent and new:
                    self._states[ent] = new

    async def get_states(self, entity_ids: list[str]) -> dict[str, Any]:
        """REST fallback for initial snapshot."""
        assert self._session
        out: dict[str, Any] = {}
        for eid in entity_ids:
            if eid in self._states:
                out[eid] = self._states[eid]
                continue
            url = f"{self._base}/api/states/{eid}"
            async with self._session.get(url) as resp:
                if resp.status == 200:
                    st = await resp.json()
                    self._states[eid] = st
                    out[eid] = st
                else:
                    logger.warning("missing entity %s status=%s", eid, resp.status)
        return out

    @staticmethod
    def state_float(state: dict[str, Any], default: float = 0.0) -> float:
        try:
            return float(state.get("state", default))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def state_bool(state: dict[str, Any], default: bool = False) -> bool:
        s = str(state.get("state", "")).lower()
        return s in ("on", "true", "yes", "1", "home", "plugged_in")

    async def set_number(self, entity_id: str, value: float) -> None:
        domain = entity_id.split(".")[0]
        service = "set_value" if domain == "number" else "turn_on"
        await self.call_service(domain, service, entity_id, {"value": value})

    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: str,
        data: Optional[dict] = None,
    ) -> None:
        assert self._session
        payload = {"entity_id": entity_id, **(data or {})}
        url = f"{self._base}/api/services/{domain}/{service}"
        async with self._session.post(url, json=payload) as resp:
            if resp.status >= 400:
                text = await resp.text()
                logger.error("service %s.%s failed: %s", domain, service, text)

    async def close(self) -> None:
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()


async def poll_states(
    client: HomeAssistantClient,
    entity_ids: list[str],
    interval_s: float,
    on_update: Callable[[dict[str, Any]], None],
) -> None:
    while True:
        states = await client.get_states(entity_ids)
        on_update(states)
        await asyncio.sleep(interval_s)
