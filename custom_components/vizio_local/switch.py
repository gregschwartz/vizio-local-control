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
    """Set up switch entities."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    vizio = hass.data[DOMAIN]["vizio"]

    async_add_entities([
        VizioMuteSwitch(coordinator, vizio),
        VizioPowerSwitch(coordinator, vizio),
    ])

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
        _LOGGER.info(f"Setting audio.mute to {value}")

        try:
            result = await self._vizio.set_setting(
                "audio",
                "mute",
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


class VizioPowerSwitch(CoordinatorEntity, SwitchEntity):
    """Vizio power switch.

    Note: Power on only works when TV is in "Quick Start" mode.
    In "Eco Mode", the TV cannot be woken via network - this is a Vizio limitation.
    """

    def __init__(self, coordinator, vizio) -> None:
        """Initialize switch entity."""
        super().__init__(coordinator)
        self._vizio = vizio
        self._attr_name = "Vizio Power"
        self._attr_unique_id = "vizio_power"

    @property
    def is_on(self) -> bool | None:
        """Return True if TV is on."""
        power_state = self.coordinator.data.get("power_state")
        if power_state is not None:
            return power_state == True or power_state == 1
        return None

    @property
    def _is_eco_mode(self) -> bool:
        """Return True if TV is in Eco Mode."""
        power_mode = self.coordinator.data.get("power_mode")
        if power_mode:
            return "eco" in str(power_mode).lower()
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        power_mode = self.coordinator.data.get("power_mode", "Unknown")
        attrs = {"power_mode": power_mode}
        if self._is_eco_mode:
            attrs["warning"] = "Power on disabled: TV in Eco Mode (change to Quick Start in TV settings)"
        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on TV (only works in Quick Start mode)."""
        if self._is_eco_mode:
            _LOGGER.warning("Cannot turn on TV: Eco Mode enabled. Change to Quick Start in TV settings.")
            return

        _LOGGER.info("Turning on TV")
        try:
            result = await self._vizio.pow_on(log_api_exception=False)
            if result:
                _LOGGER.info("Successfully turned on TV")
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("pow_on returned False")
        except Exception as e:
            _LOGGER.error(f"Exception turning on TV: {e}", exc_info=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off TV."""
        _LOGGER.info("Turning off TV")
        try:
            result = await self._vizio.pow_off(log_api_exception=False)
            if result:
                _LOGGER.info("Successfully turned off TV")
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("pow_off returned False")
        except Exception as e:
            _LOGGER.error(f"Exception turning off TV: {e}", exc_info=True)
