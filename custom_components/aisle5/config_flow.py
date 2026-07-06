"""Config flow for the Aisle 5 integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import Aisle5ApiError, Aisle5Client
from .const import CONF_API_KEY, CONF_BASE_URL, CONF_ZONE_RADIUS, DEFAULT_ZONE_RADIUS, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL): str,
        vol.Required(CONF_API_KEY): str,
    }
)


async def _validate_connection(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Raises Aisle5ApiError if the backend/API key combination doesn't work."""
    session = async_get_clientsession(hass)
    client = Aisle5Client(session, data[CONF_BASE_URL], data[CONF_API_KEY])
    await client.async_get_stores()


class Aisle5ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handles the initial setup: backend URL + API key from the app's Settings UI."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await _validate_connection(self.hass, user_input)
            except Aisle5ApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - surface any unexpected error to the user
                _LOGGER.exception("Unexpected error validating Aisle 5 connection")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_BASE_URL])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Aisle 5", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> Aisle5OptionsFlow:
        return Aisle5OptionsFlow()


class Aisle5OptionsFlow(config_entries.OptionsFlow):
    """Lets the user change the auto-created zones' radius after setup."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_radius = self.config_entry.options.get(CONF_ZONE_RADIUS, DEFAULT_ZONE_RADIUS)
        schema = vol.Schema(
            {
                vol.Required(CONF_ZONE_RADIUS, default=current_radius): vol.All(
                    vol.Coerce(int), vol.Range(min=10, max=5000)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
