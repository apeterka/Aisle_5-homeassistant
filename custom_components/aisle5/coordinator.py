"""DataUpdateCoordinator for the Aisle 5 integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Aisle5ApiError, Aisle5Client
from .const import DOMAIN, UPDATE_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)


class Aisle5Coordinator(DataUpdateCoordinator[dict[int, dict]]):
    """Fetches stores and their items, keyed by store id.

    Refreshes on the fixed interval below as a fallback, but the webhook
    receiver in __init__.py also calls async_request_refresh() immediately
    whenever the backend pushes a change, so real-world staleness is usually
    seconds, not minutes.
    """

    def __init__(self, hass: HomeAssistant, client: Aisle5Client) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        self.client = client

    async def _async_update_data(self) -> dict[int, dict]:
        try:
            stores = await self.client.async_get_stores()
            for store in stores:
                store["items"] = await self.client.async_get_items(store["id"])
            return {store["id"]: store for store in stores}
        except Aisle5ApiError as err:
            raise UpdateFailed(str(err)) from err
