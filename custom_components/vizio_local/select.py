"""Select entity for Vizio TV source."""
from __future__ import annotations

import logging
import time

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Physical inputs, hardcoded so they're always valid options even when the
# TV is in standby (its inputs endpoint goes dark in Eco Mode). The list
# fetched from the TV is merged on top in case of renames.
KNOWN_INPUTS = ["CAST", "HDMI-1", "HDMI-2", "HDMI-3", "HDMI-4", "HDMI-5", "COMP"]

# Retry backoff for loading the inputs list (seconds)
RETRY_INITIAL = 10
RETRY_MAX = 300

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
    """Vizio source selector (inputs + apps).

    Physical inputs are seeded from KNOWN_INPUTS so options like HDMI-2
    stay valid even when HA starts while the TV is in standby (the inputs
    endpoint goes dark in Eco Mode). The combined options list never
    shrinks - otherwise automations referencing an input break.
    """

    def __init__(self, coordinator, vizio) -> None:
        """Initialize select entity."""
        super().__init__(coordinator)
        self._vizio = vizio
        self._attr_name = "Vizio Source"
        self._attr_unique_id = "vizio_source"
        self._inputs = list(KNOWN_INPUTS)
        self._apps = []
        self._all_options = list(KNOWN_INPUTS)
        self._retry_delay = RETRY_INITIAL
        self._next_retry = 0.0
        self._loading = False
        self._apps_loaded = False

    async def async_added_to_hass(self) -> None:
        """Load options when added to hass."""
        await super().async_added_to_hass()
        await self._try_load_options()

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Retry until the app list has loaded, with backoff so a sleeping
        # TV isn't hammered every poll cycle
        now = time.monotonic()
        if not self._apps_loaded and not self._loading and now >= self._next_retry:
            self._next_retry = now + self._retry_delay
            self._retry_delay = min(self._retry_delay * 2, RETRY_MAX)
            self.hass.async_create_task(self._try_load_options())
        super()._handle_coordinator_update()

    async def _try_load_options(self) -> None:
        """Try to load options, handling errors."""
        self._loading = True
        try:
            await self._async_update_options()
        except Exception as e:
            _LOGGER.error(f"Failed to load source options: {e}", exc_info=True)
        finally:
            self._loading = False

    def _rebuild_options(self) -> None:
        """Combine inputs + apps into the options list, never shrinking."""
        combined = self._inputs + self._apps
        for existing in self._all_options:
            if existing not in combined:
                combined.append(existing)
        self._all_options = combined

    async def _async_update_options(self) -> None:
        """Update available options."""
        # Get inputs
        _LOGGER.debug("Fetching inputs list...")
        inputs = await self._vizio.get_inputs_list(log_api_exception=False)
        _LOGGER.debug(f"Raw inputs response: {inputs} (type: {type(inputs).__name__})")
        if inputs:
            fetched = [inp.name for inp in inputs]
            # Merge instead of replace so a partial answer can't drop inputs
            for name in fetched:
                if name not in self._inputs:
                    self._inputs.append(name)
            self._retry_delay = RETRY_INITIAL
            _LOGGER.info(f"Loaded {len(self._inputs)} inputs: {self._inputs}")
        else:
            _LOGGER.debug("No inputs returned from TV (likely standby)")

        # Get apps
        _LOGGER.debug("Fetching apps list...")
        apps = await self._vizio.get_apps_list()
        if apps:
            # Apps are returned as strings, not objects
            self._apps = sorted(apps)
            self._apps_loaded = True
            _LOGGER.debug(f"Loaded {len(self._apps)} apps")
        else:
            _LOGGER.debug("No apps returned from TV")

        self._rebuild_options()
        _LOGGER.debug(f"Total options available: {len(self._all_options)}")
        self.async_write_ha_state()

    @property
    def options(self) -> list[str]:
        """Return list of available options."""
        return self._all_options

    @property
    def current_option(self) -> str | None:
        """Return current source."""
        current = self.coordinator.data.get("current_source")
        # Add to options if not present so HA doesn't reject the value
        if current and current not in self._all_options:
            self._all_options.append(current)
        return current

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return len(self._all_options) > 0

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
