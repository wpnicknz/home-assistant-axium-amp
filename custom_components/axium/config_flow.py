from __future__ import annotations
from typing import Any
from homeassistant import config_entries
import voluptuous as vol

from .const import DOMAIN, DEFAULT_ZONES, DEFAULT_SCAN_INTERVAL

class AxiumConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            zones_str: str = user_input["zones"]
            zones = [int(z.strip()) for z in zones_str.split(',') if z.strip()]
            data = {
                "host": user_input["host"],
                "zones": zones,
                "scan_interval": user_input["scan_interval"],
            }
            return self.async_create_entry(title=f"Axium {user_input['host']}", data=data)

        schema = vol.Schema({
            vol.Required("host"): str,
            vol.Required("zones", default=",".join(map(str, DEFAULT_ZONES))): str,
            vol.Required("scan_interval", default=DEFAULT_SCAN_INTERVAL): int,
        })
        return self.async_show_form(step_id="user", data_schema=schema)
