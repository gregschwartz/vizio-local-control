"""Switch entity for Vizio TV mute."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up switch entity."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    vizio = hass.data[DOMAIN]["vizio"]

    async_add_entities([VizioMuteSwitch(coordinator, vizio)])

class VizioMuteSwitch(CoordinatorEntity, SwitchEntity):
    """Vizio mute switch."""

    def __init__(self, coordinator, vizio) -> None:
        """Initialize switch entity."""
        super().__init__(coordinator)
        self._vizio = vizio
        self._attr_name = "Vizio Mute"
        self._attr_unique_id = "vizio_mute"

    @property
    def is_on(self) -> bool | None:
        """Return True if muted."""
        mute_value = self.coordinator.data.get("audio_mute")
        if mute_value is not None:
            return mute_value == "On"
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Mute TV."""
        try:
            current_hash = self.coordinator.data.get("audio_mute_hash")

            if current_hash is None:
                item = await self._vizio.get_setting("audio", "mute", log_api_exception=False)
                if item:
                    current_hash = item.id

            if current_hash is not None:
                result = await self._vizio.set_setting(
                    "audio",
                    "mute",
                    current_hash,
                    "On",
                    log_api_exception=False,
                )
                if result:
                    await self.coordinator.async_request_refresh()
                else:
                    _LOGGER.error("Failed to mute TV")
            else:
                _LOGGER.error("Could not get hash for mute")

        except Exception as e:
            _LOGGER.error(f"Error muting TV: {e}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Unmute TV."""
        try:
            current_hash = self.coordinator.data.get("audio_mute_hash")

            if current_hash is None:
                item = await self._vizio.get_setting("audio", "mute", log_api_exception=False)
                if item:
                    current_hash = item.id

            if current_hash is not None:
                result = await self._vizio.set_setting(
                    "audio",
                    "mute",
                    current_hash,
                    "Off",
                    log_api_exception=False,
                )
                if result:
                    await self.coordinator.async_request_refresh()
                else:
                    _LOGGER.error("Failed to unmute TV")
            else:
                _LOGGER.error("Could not get hash for mute")

        except Exception as e:
            _LOGGER.error(f"Error unmuting TV: {e}")
