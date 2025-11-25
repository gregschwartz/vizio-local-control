"""Number entities for Vizio TV."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

PICTURE_SETTINGS = {
    "backlight": {"min": 0, "max": 100, "step": 1},
    "brightness": {"min": 0, "max": 100, "step": 1},
    "contrast": {"min": 0, "max": 100, "step": 1},
    "color": {"min": 0, "max": 100, "step": 1},
    "tint": {"min": 0, "max": 100, "step": 1},
    "sharpness": {"min": 0, "max": 100, "step": 1},
}

AUDIO_SETTINGS = {
    "volume": {"min": 0, "max": 100, "step": 1},
    "balance": {"min": -50, "max": 50, "step": 1},
}

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up number entities."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    vizio = hass.data[DOMAIN]["vizio"]

    entities = []

    # Picture settings
    for setting_name, config in PICTURE_SETTINGS.items():
        entities.append(
            VizioNumberEntity(
                coordinator,
                vizio,
                setting_name,
                "picture",
                config["min"],
                config["max"],
                config["step"],
            )
        )

    # Audio settings
    for setting_name, config in AUDIO_SETTINGS.items():
        entities.append(
            VizioNumberEntity(
                coordinator,
                vizio,
                setting_name,
                "audio",
                config["min"],
                config["max"],
                config["step"],
            )
        )

    async_add_entities(entities)

class VizioNumberEntity(CoordinatorEntity, NumberEntity):
    """Vizio number entity."""

    def __init__(
        self,
        coordinator,
        vizio,
        setting_name: str,
        setting_type: str,
        min_value: float,
        max_value: float,
        step: float,
    ) -> None:
        """Initialize number entity."""
        super().__init__(coordinator)
        self._vizio = vizio
        self._setting_name = setting_name
        self._setting_type = setting_type
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_name = f"Vizio {setting_name.replace('_', ' ').title()}"
        self._attr_unique_id = f"vizio_{setting_type}_{setting_name}"

    @property
    def native_value(self) -> float | None:
        """Return current value."""
        key = f"{self._setting_type}_{self._setting_name}"
        value = self.coordinator.data.get(key)
        if value is not None:
            if isinstance(value, str):
                return 0 if value == "Off" else 1
            return float(value)
        return None

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        try:
            hash_key = f"{self._setting_type}_{self._setting_name}_hash"
            current_hash = self.coordinator.data.get(hash_key)

            if current_hash is None:
                item = await self._vizio.get_setting(
                    self._setting_type, self._setting_name, log_api_exception=False
                )
                if item:
                    current_hash = item.id

            if current_hash is not None:
                result = await self._vizio.set_setting(
                    self._setting_type,
                    self._setting_name,
                    current_hash,
                    int(value),
                    log_api_exception=False,
                )
                if result:
                    await self.coordinator.async_request_refresh()
                else:
                    _LOGGER.error(f"Failed to set {self._setting_name} to {value}")
            else:
                _LOGGER.error(f"Could not get hash for {self._setting_name}")

        except Exception as e:
            _LOGGER.error(f"Error setting {self._setting_name}: {e}")
