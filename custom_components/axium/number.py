from __future__ import annotations
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.number import NumberEntity, NumberMode

from .entity import AxiumEntity
from .coordinator import AxiumCoordinator, encode_zone

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data["axium"][entry.entry_id]
    coord: AxiumCoordinator = data["coordinator"]
    entities = [AxiumVolumeNumber(coord, z) for z in coord.zones]
    async_add_entities(entities)

class AxiumVolumeNumber(AxiumEntity, NumberEntity):
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0
    _attr_native_max_value = 160
    _attr_native_step = 1
    _attr_icon = "mdi:volume-high"

    def __init__(self, coordinator: AxiumCoordinator, zone: int):
        super().__init__(coordinator, zone)
        self._attr_name = f"Z{zone} Volume"
        self._attr_unique_id = f"axium_z{zone}_volume"

    @property
    def name(self):
        base = self.coordinator.zone_names.get(self.zone) or f"Axium Z{self.zone}"
        return f"{base} Volume"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.volume.get(self.zone)

    async def async_set_native_value(self, value: float) -> None:
        v = max(0, min(160, int(value)))
        hexv = f"{v:02X}"
        await self.coordinator.api.send(f"04{encode_zone(self.zone)}{hexv}")
        self.coordinator.volume[self.zone] = v
        self.async_write_ha_state()
