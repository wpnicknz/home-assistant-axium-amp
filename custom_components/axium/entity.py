from __future__ import annotations
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from .coordinator import AxiumCoordinator
from .const import DOMAIN

class AxiumEntity(CoordinatorEntity[AxiumCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: AxiumCoordinator, zone: int):
        super().__init__(coordinator)
        self.zone = zone

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"axium_z{self.zone}")},
            name=self.coordinator.zone_names.get(self.zone) or f"Axium Z{self.zone}",
            manufacturer="Axium",
            model="AX-series",
        )
