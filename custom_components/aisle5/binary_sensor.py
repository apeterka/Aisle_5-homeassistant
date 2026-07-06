"""Binary sensor platform for Aisle 5 - 'currently open' per store."""
from __future__ import annotations

import json

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import Aisle5Coordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Sets up one 'open now' binary sensor per known store."""
    coordinator: Aisle5Coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    known_store_ids: set[int] = set()

    def _sync_entities() -> None:
        new_ids = set(coordinator.data) - known_store_ids
        if not new_ids:
            return
        known_store_ids.update(new_ids)
        async_add_entities(Aisle5OpenSensor(coordinator, store_id) for store_id in new_ids)

    _sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_sync_entities))


class Aisle5OpenSensor(CoordinatorEntity[Aisle5Coordinator], BinarySensorEntity):
    """Whether a store is currently open, computed from its opening-hours schedule.

    Aisle 5 stores `openingHours` as JSON keyed by JS weekday index
    (0 = Sunday ... 6 = Saturday), each entry shaped like
    {"open": "08:00", "close": "20:00", "closed": false}.
    """

    def __init__(self, coordinator: Aisle5Coordinator, store_id: int) -> None:
        super().__init__(coordinator)
        self._store_id = store_id
        self._attr_unique_id = f"aisle5_store_{store_id}_open"

    @property
    def _store(self) -> dict:
        return self.coordinator.data.get(self._store_id, {})

    @property
    def name(self) -> str:
        store_name = self._store.get("name", f"Laden {self._store_id}")
        return f"{store_name} geöffnet"

    @property
    def is_on(self) -> bool | None:
        raw_schedule = self._store.get("openingHours")
        if not raw_schedule:
            return None
        try:
            schedule = json.loads(raw_schedule)
        except (TypeError, ValueError):
            return None

        now = dt_util.now()
        js_weekday = (now.weekday() + 1) % 7  # Python Monday=0 -> JS Sunday=0
        today = schedule.get(str(js_weekday))
        if not today or today.get("closed"):
            return False

        current_time = now.strftime("%H:%M")
        return today["open"] <= current_time <= today["close"]
