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
        # Start with loading placeholder so entity isn't unavailable
        self._all_options = ["Loading..."]

    async def async_added_to_hass(self) -> None:
        """Load options when added to hass."""
        await super().async_added_to_hass()
        try:
            await self._async_update_options()
        except Exception as e:
            _LOGGER.error(f"Failed to load source options: {e}", exc_info=True)
            # Set fallback options
            self._all_options = ["Error loading sources"]

    async def _async_update_options(self) -> None:
        """Update available options."""
        try:
            # Get inputs
            _LOGGER.debug("Fetching inputs list...")
            inputs = await self._vizio.get_inputs_list(log_api_exception=False)
            if inputs:
                self._inputs = [inp.name for inp in inputs]
                _LOGGER.info(f"Loaded {len(self._inputs)} inputs: {self._inputs}")
            else:
                _LOGGER.warning("No inputs returned from TV")

            # Get apps
            _LOGGER.debug("Fetching apps list...")
            apps = await self._vizio.get_apps_list()
            if apps:
                # Apps are returned as strings, not objects
                self._apps = sorted(apps)
                _LOGGER.info(f"Loaded {len(self._apps)} apps")
            else:
                _LOGGER.warning("No apps returned from TV")

            # Combine: inputs first, then apps
            if self._inputs or self._apps:
                self._all_options = self._inputs + self._apps
                _LOGGER.info(f"Total options available: {len(self._all_options)}")
            else:
                _LOGGER.error("No inputs or apps loaded - TV may be off or unreachable")
                self._all_options = ["TV unreachable"]

        except Exception as e:
            _LOGGER.error(f"Error updating source options: {e}", exc_info=True)
            self._all_options = ["Error loading sources"]

    @property
    def options(self) -> list[str]:
        """Return list of available options."""
        return self._all_options

    @property
    def current_option(self) -> str | None:
        """Return current source."""
        current = self.coordinator.data.get("current_source")
        _LOGGER.debug(f"Current source from coordinator: {current}")
        return current

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Entity is available if we have real options (not error messages)
        return len(self._all_options) > 0 and self._all_options[0] not in ["Loading...", "Error loading sources", "TV unreachable"]

    async def async_select_option(self, option: str) -> None:
        """Select new source."""
        try:
            # Check if it's an input or app
            if option in self._inputs:
                # It's an input
                _LOGGER.info(f"Switching to input: {option}")
                result = await self._vizio.set_input(option, log_api_exception=False)
                if result:
                    _LOGGER.info(f"Successfully switched to input: {option}")
                    await self.coordinator.async_request_refresh()
                else:
                    _LOGGER.error(f"Failed to switch to input: {option}")
            elif option in self._apps:
                # It's an app
                _LOGGER.info(f"Launching app: {option}")
                result = await self._vizio.launch_app(option, log_api_exception=False)
                if result:
                    _LOGGER.info(f"Successfully launched app: {option}")
                    await self.coordinator.async_request_refresh()
                else:
                    _LOGGER.error(f"Failed to launch app: {option}")
            else:
                _LOGGER.error(f"Unknown source: {option} (not in inputs or apps)")

        except Exception as e:
            _LOGGER.error(f"Error selecting source {option}: {e}", exc_info=True)
