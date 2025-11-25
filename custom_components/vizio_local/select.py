"""Select entity for Vizio TV source."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
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
    """Set up select entity."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    vizio = hass.data[DOMAIN]["vizio"]

    async_add_entities([VizioSourceSelect(coordinator, vizio)])

class VizioSourceSelect(CoordinatorEntity, SelectEntity):
    """Vizio source selector (inputs + apps)."""

    def __init__(self, coordinator, vizio) -> None:
        """Initialize select entity."""
        super().__init__(coordinator)
        self._vizio = vizio
        self._attr_name = "Vizio Source"
        self._attr_unique_id = "vizio_source"
        self._inputs = []
        self._apps = []
        self._all_options = []

    async def async_added_to_hass(self) -> None:
        """Load options when added to hass."""
        await super().async_added_to_hass()
        await self._async_update_options()

    async def _async_update_options(self) -> None:
        """Update available options."""
        # Get inputs
        inputs = await self._vizio.get_inputs_list(log_api_exception=False)
        if inputs:
            self._inputs = [inp.name for inp in inputs]

        # Get apps
        apps = await self._vizio.get_apps_list(log_api_exception=False)
        if apps:
            self._apps = sorted([app.name for app in apps])

        # Combine: inputs first, then apps
        self._all_options = self._inputs + self._apps

        _LOGGER.info(f"Loaded {len(self._inputs)} inputs and {len(self._apps)} apps")

    @property
    def options(self) -> list[str]:
        """Return list of available options."""
        return self._all_options

    @property
    def current_option(self) -> str | None:
        """Return current source."""
        return self.coordinator.data.get("current_source")

    async def async_select_option(self, option: str) -> None:
        """Select new source."""
        try:
            # Check if it's an input or app
            if option in self._inputs:
                # It's an input
                result = await self._vizio.set_input(option, log_api_exception=False)
                if result:
                    _LOGGER.info(f"Switched to input: {option}")
                    await self.coordinator.async_request_refresh()
                else:
                    _LOGGER.error(f"Failed to switch to input: {option}")
            elif option in self._apps:
                # It's an app
                result = await self._vizio.launch_app(option, log_api_exception=False)
                if result:
                    _LOGGER.info(f"Launched app: {option}")
                    await self.coordinator.async_request_refresh()
                else:
                    _LOGGER.error(f"Failed to launch app: {option}")
            else:
                _LOGGER.error(f"Unknown source: {option}")

        except Exception as e:
            _LOGGER.error(f"Error selecting source {option}: {e}")
