"""Thin async client for the Aisle 5 backend API."""
from __future__ import annotations

from typing import Any

import aiohttp

DEFAULT_ITEM_QUANTITY = 1
DEFAULT_ITEM_UNIT = "Stk."


class Aisle5ApiError(Exception):
    """Raised when the Aisle 5 backend returns an error or is unreachable."""


class Aisle5Client:
    """Talks to the Aisle 5 backend using the machine `X-API-Key` auth."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str, api_key: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-API-Key": api_key}

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=10),
                **kwargs,
            ) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400:
                    message = (payload or {}).get("message", f"HTTP {response.status}")
                    raise Aisle5ApiError(message)
                return payload.get("data", payload) if isinstance(payload, dict) else payload
        except aiohttp.ClientError as err:
            raise Aisle5ApiError(str(err)) from err

    async def async_get_stores(self) -> list[dict]:
        """Fetches all stores for the API key's owner."""
        return await self._request("GET", "/api/stores")

    async def async_get_items(self, store_id: int) -> list[dict]:
        """Fetches all items for a given store."""
        return await self._request("GET", f"/api/stores/{store_id}/items")

    async def async_add_item(self, store_id: int, name: str) -> dict:
        """Adds a new item to a store's list."""
        return await self._request(
            "POST",
            f"/api/stores/{store_id}/items",
            json={"name": name, "quantity": DEFAULT_ITEM_QUANTITY, "unit": DEFAULT_ITEM_UNIT},
        )

    async def async_update_item(self, item_id: str, **fields: Any) -> dict:
        """Updates fields of an existing item (e.g. isChecked)."""
        return await self._request("PUT", f"/api/items/{item_id}", json=fields)

    async def async_delete_item(self, item_id: str) -> None:
        """Deletes an item."""
        await self._request("DELETE", f"/api/items/{item_id}")

    async def async_register_webhook(self, url: str) -> dict:
        """Registers this Home Assistant instance's webhook URL with the backend."""
        return await self._request("POST", "/api/ha/webhooks", json={"url": url})
