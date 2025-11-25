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

    async def _set_mute(self, value: str) -> bool:
        """Set mute state (internal helper)."""
        _LOGGER.info(f"Attempting to set mute to {value}")

        try:
            # Get current item to retrieve HASHVAL
            _LOGGER.debug("Fetching current mute setting to get HASHVAL")
            item = await self._vizio.get_setting("audio", "mute", log_api_exception=False)

            if not item:
                _LOGGER.error("Could not retrieve current mute - item is None")
                return False

            # Extract hash - handle both Item objects and raw values
            current_hash = None
            if hasattr(item, 'id'):
                current_hash = item.id
                _LOGGER.debug(f"Got hash from item.id: {current_hash}")
            else:
                _LOGGER.error(f"Item returned for mute has no 'id' attribute: {type(item)}")
                return False

            if current_hash is None:
                _LOGGER.error("HASHVAL is None for mute")
                return False

            # Set the new value
            _LOGGER.info(f"Setting audio.mute = {value} with hash {current_hash}")
            result = await self._vizio.set_setting(
                "audio",
                "mute",
                current_hash,
                value,
                log_api_exception=False,
            )

            if result:
                _LOGGER.info(f"Successfully set mute to {value}")
                await self.coordinator.async_request_refresh()
                return True
            else:
                _LOGGER.error(f"set_setting returned False for mute = {value}")
                return False

        except Exception as e:
            _LOGGER.error(f"Exception setting mute: {e}", exc_info=True)
            return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Mute TV."""
        await self._set_mute("On")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Unmute TV."""
        await self._set_mute("Off")
