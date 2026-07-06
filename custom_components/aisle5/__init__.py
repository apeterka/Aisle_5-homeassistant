"""The Aisle 5 integration: stores, shopping lists and location reminders."""
from __future__ import annotations

import hashlib
import hmac
import logging

from aiohttp import web
from homeassistant.components import webhook
from homeassistant.components.zone import DOMAIN as ZONE_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.util import slugify

from .api import Aisle5ApiError, Aisle5Client
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_WEBHOOK_ID,
    CONF_WEBHOOK_SECRET,
    CONF_ZONE_ENTRIES,
    CONF_ZONE_RADIUS,
    DEFAULT_ZONE_RADIUS,
    DOMAIN,
)
from .coordinator import Aisle5Coordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.TODO, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Aisle 5 from a config entry."""
    session = async_get_clientsession(hass)
    client = Aisle5Client(session, entry.data[CONF_BASE_URL], entry.data[CONF_API_KEY])
    coordinator = Aisle5Coordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await _async_ensure_zones(hass, entry, coordinator.data)
    await _async_setup_webhook(hass, entry, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    webhook_id = entry.data.get(CONF_WEBHOOK_ID)
    if webhook_id:
        webhook.async_unregister(hass, webhook_id)

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_ensure_zones(
    hass: HomeAssistant, entry: ConfigEntry, stores: dict[int, dict]
) -> None:
    """Creates or updates one HA zone per store that has coordinates.

    Zones (like input_boolean, counter, person, ...) are managed through
    Home Assistant's Storage Collection helper, not through config_entries/
    config_flow - that's what the "Add Zone" button in Settings actually
    calls under the hood. hass.data[ZONE_DOMAIN] holds that collection once
    the zone integration has set itself up.

    The collection item id of each zone we create is tracked in our own
    config entry's data (CONF_ZONE_ENTRIES), so a later sync (e.g. after the
    radius option changes, or a store's coordinates change) updates the
    existing zone in place instead of only ever creating it once.
    """
    zone_collection = hass.data.get(ZONE_DOMAIN)
    if zone_collection is None:
        _LOGGER.warning("Zone storage collection not available yet - skipping zone sync")
        return

    radius = entry.options.get(CONF_ZONE_RADIUS, DEFAULT_ZONE_RADIUS)
    zone_entries: dict[str, str] = dict(entry.data.get(CONF_ZONE_ENTRIES, {}))
    changed = False

    stores_with_coords = [
        s for s in stores.values() if s.get("latitude") is not None and s.get("longitude") is not None
    ]
    _LOGGER.info(
        "Aisle 5 zone sync: %d/%d stores have coordinates", len(stores_with_coords), len(stores)
    )

    for store_id, store in stores.items():
        latitude, longitude = store.get("latitude"), store.get("longitude")
        if latitude is None or longitude is None:
            continue

        store_key = str(store_id)
        zone_data = {
            "name": store["name"],
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius,
            "icon": "mdi:cart",
            "passive": False,
        }

        tracked_item_id = zone_entries.get(store_key)

        try:
            if tracked_item_id is not None and tracked_item_id in zone_collection.data:
                existing = zone_collection.data[tracked_item_id]
                if any(existing.get(key) != value for key, value in zone_data.items()):
                    await zone_collection.async_update_item(tracked_item_id, zone_data)
                    _LOGGER.debug("Updated existing zone for store '%s'", store["name"])
                continue

            entity_id = f"zone.{slugify(store['name'])}"
            if hass.states.get(entity_id):
                # A zone with this name already exists and we don't own it
                # (e.g. created manually) - don't create a duplicate.
                _LOGGER.warning(
                    "Zone entity '%s' already exists but isn't tracked by Aisle 5 - "
                    "skipping to avoid a duplicate (rename it or the store to resolve)",
                    entity_id,
                )
                continue

            new_item = await zone_collection.async_create_item(zone_data)
            zone_entries[store_key] = new_item["id"]
            changed = True
            _LOGGER.debug("Created zone for store '%s'", store["name"])
        except Exception as err:  # noqa: BLE001 - a single bad store must not block setup
            _LOGGER.warning(
                "Could not create/update zone for store '%s': %s", store["name"], err
            )

    if changed:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_ZONE_ENTRIES: zone_entries}
        )


async def _async_setup_webhook(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: Aisle5Coordinator
) -> None:
    """Registers this HA instance's webhook with the backend (once) and listens for pushes."""
    webhook_id = entry.data.get(CONF_WEBHOOK_ID)
    secret = entry.data.get(CONF_WEBHOOK_SECRET)

    if not webhook_id:
        webhook_id = webhook.async_generate_id()
        try:
            # Prefer the externally configured URL: the Aisle 5 backend is
            # commonly hosted elsewhere (its own server/VM), not necessarily
            # on the same LAN as Home Assistant, so the default internal-first
            # behavior of webhook.async_generate_url() would produce an
            # unreachable local IP for that backend to call back to.
            base_url = get_url(hass, allow_internal=True, prefer_external=True)
        except NoURLAvailableError:
            _LOGGER.warning(
                "No usable Home Assistant URL configured (Settings > System > "
                "Network) - cannot register the Aisle 5 webhook, falling back "
                "to polling only"
            )
            return
        webhook_url = f"{base_url}/api/webhook/{webhook_id}"
        client: Aisle5Client = hass.data[DOMAIN][entry.entry_id]["client"]
        try:
            result = await client.async_register_webhook(webhook_url)
        except Aisle5ApiError as err:
            _LOGGER.warning(
                "Could not register the Aisle 5 webhook (falling back to polling only): %s", err
            )
            return
        secret = result["secret"]
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_WEBHOOK_ID: webhook_id, CONF_WEBHOOK_SECRET: secret},
        )

    async def _handle_webhook(hass: HomeAssistant, webhook_id: str, request: web.Request):
        body = await request.read()
        signature = request.headers.get("X-Aisle5-Signature", "")
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            _LOGGER.warning("Rejected Aisle 5 webhook call with an invalid signature")
            return web.Response(status=401)

        await coordinator.async_request_refresh()
        return web.Response(status=200)

    webhook.async_register(hass, DOMAIN, "Aisle 5", webhook_id, _handle_webhook)
