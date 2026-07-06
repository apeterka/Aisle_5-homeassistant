"""Todo platform for Aisle 5 - one list per store."""
from __future__ import annotations

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Aisle5Coordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Sets up one todo list entity per known store, adding new ones as they appear."""
    coordinator: Aisle5Coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    known_store_ids: set[int] = set()

    def _sync_entities() -> None:
        new_ids = set(coordinator.data) - known_store_ids
        if not new_ids:
            return
        known_store_ids.update(new_ids)
        async_add_entities(Aisle5TodoList(coordinator, store_id) for store_id in new_ids)

    _sync_entities()
    entry.async_on_unload(coordinator.async_add_listener(_sync_entities))


class Aisle5TodoList(CoordinatorEntity[Aisle5Coordinator], TodoListEntity):
    """A single store's shopping list, mirrored as a native HA todo list."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(self, coordinator: Aisle5Coordinator, store_id: int) -> None:
        super().__init__(coordinator)
        self._store_id = store_id
        self._attr_unique_id = f"aisle5_store_{store_id}_list"

    @property
    def _store(self) -> dict:
        return self.coordinator.data.get(self._store_id, {})

    @property
    def name(self) -> str:
        return self._store.get("name", f"Laden {self._store_id}")

    @property
    def todo_items(self) -> list[TodoItem]:
        return [
            TodoItem(
                summary=f"{item['quantity']} {item['unit']} {item['name']}".strip(),
                uid=str(item["id"]),
                status=(
                    TodoItemStatus.COMPLETED
                    if item.get("isChecked")
                    else TodoItemStatus.NEEDS_ACTION
                ),
            )
            for item in self._store.get("items", [])
        ]

    async def async_create_todo_item(self, item: TodoItem) -> None:
        await self.coordinator.client.async_add_item(self._store_id, item.summary)
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        await self.coordinator.client.async_update_item(
            item.uid, isChecked=item.status == TodoItemStatus.COMPLETED
        )
        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        for uid in uids:
            await self.coordinator.client.async_delete_item(uid)
        await self.coordinator.async_request_refresh()
