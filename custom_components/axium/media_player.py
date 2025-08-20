from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from .entity import AxiumEntity
from .coordinator import AxiumCoordinator, encode_zone, ENCODE_SOURCE_MAP

SUPPORT_FLAGS = (
    MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data["axium"][entry.entry_id]
    coord: AxiumCoordinator = data["coordinator"]
    entities = [AxiumZonePlayer(coord, z) for z in coord.zones]
    async_add_entities(entities)

class AxiumZonePlayer(AxiumEntity, MediaPlayerEntity):
    _attr_supported_features = SUPPORT_FLAGS

    def __init__(self, coordinator: AxiumCoordinator, zone: int):
        super().__init__(coordinator, zone)
        self._attr_name = f"Zone {zone}"
        self._attr_unique_id = f"axium_media_z{zone}"

    @property
    def state(self):
        p = self.coordinator.power.get(self.zone)
        if p == "on":
            return MediaPlayerState.ON
        if p == "off":
            return MediaPlayerState.OFF
        return None

    async def async_turn_on(self):
        await self.coordinator.api.send(f"01{encode_zone(self.zone)}01")

    async def async_turn_off(self):
        await self.coordinator.api.send(f"01{encode_zone(self.zone)}00")

    @property
    def volume_level(self) -> float | None:
        v = self.coordinator.volume.get(self.zone)
        mv = self.coordinator.max_vol.get(self.zone) or 160
        if v is None:
            return None
        return max(0.0, min(1.0, v / mv))

    async def async_set_volume_level(self, volume: float) -> None:
        mv = self.coordinator.max_vol.get(self.zone) or 160
        raw = int(round(max(0.0, min(1.0, volume)) * mv))
        await self.coordinator.api.send(f"04{encode_zone(self.zone)}{raw:02X}")

    @property
    def source_list(self) -> list[str] | None:
        names = self.coordinator.source_names.get(self.zone, {})
        return [names.get(i, f"S{i+1}") for i in range(8)]

    @property
    def source(self) -> str | None:
        cur = self.coordinator.source.get(self.zone)
        if cur is None:
            return None
        names = self.coordinator.source_names.get(self.zone, {})
        return names.get(cur, f"S{cur+1}")

    async def async_select_source(self, source: str) -> None:
        names = self.coordinator.source_names.get(self.zone, {})
        for i in range(8):
            if names.get(i, f"S{i+1}") == source:
                idx = i
                break
        else:
            if source and source.upper().startswith("S"):
                try:
                    idx = int(source[1:]) - 1
                except Exception:
                    return
            else:
                return
        ax_val = ENCODE_SOURCE_MAP.get(idx, idx)
        await self.coordinator.api.send(f"03{encode_zone(self.zone)}{ax_val:02X}")
