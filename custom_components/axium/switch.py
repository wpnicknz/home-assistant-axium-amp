from __future__ import annotations
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.switch import SwitchEntity

from .entity import AxiumEntity
from .coordinator import AxiumCoordinator, encode_zone

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data["axium"][entry.entry_id]
    coord: AxiumCoordinator = data["coordinator"]
    entities = [AxiumPowerSwitch(coord, z) for z in coord.zones]
    async_add_entities(entities)

class AxiumPowerSwitch(AxiumEntity, SwitchEntity):
    _attr_icon = "mdi:power"

    def __init__(self, coordinator: AxiumCoordinator, zone: int):
        super().__init__(coordinator, zone)
        self._attr_name = f"Z{zone} Power"
        self._attr_unique_id = f"axium_z{zone}_power"

    @property
    def name(self):
        base = self.coordinator.zone_names.get(self.zone) or f"Axium Z{self.zone}"
        return f"{base} Power"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.power.get(self.zone) == "on"

    async def async_turn_on(self, **kwargs):
        await self.coordinator.api.send(f"01{encode_zone(self.zone)}01")
        self.coordinator.power[self.zone] = "on"
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.api.send(f"01{encode_zone(self.zone)}00")
        self.coordinator.power[self.zone] = "off"
        self.async_write_ha_state()
