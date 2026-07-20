"""Vizio Local Control integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from pyvizio import VizioAsync

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import discovery

_LOGGER = logging.getLogger(__name__)

DOMAIN = "vizio_local"
PLATFORMS = [Platform.NUMBER, Platform.SELECT, Platform.SWITCH]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up from configuration.yaml."""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    host = conf.get("host")
    port = conf.get("port", 7345)
    token = conf.get("access_token")

    if not host or not token:
        _LOGGER.error("Missing required configuration: host and access_token")
        return False

    # Create Vizio client
    vizio = VizioAsync("0.0.0.0", f"{host}:{port}", "Vizio Greg", token, "tv")

    async def async_update_data():
        """Fetch data from Vizio."""
        data = {}

        # get_setting returns int/str directly (not Item objects)
        for setting in ["backlight", "brightness", "contrast", "color", "tint", "sharpness"]:
            try:
                val = await vizio.get_setting("picture", setting, log_api_exception=False)
                if val is not None:
                    data[f"picture_{setting}"] = val
                    _LOGGER.debug(f"Got picture {setting}: {val}")
            except Exception as e:
                _LOGGER.warning(f"Failed to get picture {setting}: {e}")

        for setting in ["volume", "mute"]:
            try:
                val = await vizio.get_setting("audio", setting, log_api_exception=False)
                if val is not None:
                    data[f"audio_{setting}"] = val
                    _LOGGER.debug(f"Got audio {setting}: {val}")
                else:
                    _LOGGER.warning(f"No data returned for audio {setting}")
            except Exception as e:
                _LOGGER.warning(f"Failed to get audio {setting}: {e}")

        # Get current input/app
        try:
            current_input = await vizio.get_current_input(log_api_exception=False)
            _LOGGER.debug(f"Raw get_current_input returned: {current_input!r}")

            # If on SmartCast input (or input is None while TV is on), try to get app
            if not current_input or (current_input and current_input.upper() == "SMARTCAST"):
                current_app = await vizio.get_current_app(log_api_exception=False)
                _LOGGER.debug(f"Raw get_current_app returned: {current_app!r}")
                if current_app and current_app != "_UNKNOWN_APP":
                    data["current_source"] = current_app
                elif current_input:
                    data["current_source"] = current_input
                else:
                    data["current_source"] = "SmartCast"
            else:
                data["current_source"] = current_input
                _LOGGER.debug(f"Current source: {current_input} (input)")
        except Exception as e:
            _LOGGER.warning(f"Failed to get current input/app: {e}")

        # Get power state
        try:
            power_state = await vizio.get_power_state(log_api_exception=False)
            data["power_state"] = power_state
            _LOGGER.debug(f"Power state: {power_state}")
        except Exception as e:
            _LOGGER.warning(f"Failed to get power state: {e}")

        # Get power mode (Eco Mode vs Quick Start) - needed for power switch
        try:
            val = await vizio.get_setting("system", "power_mode", log_api_exception=False)
            if val is not None:
                data["power_mode"] = val
                _LOGGER.debug(f"Power mode: {val}")
        except Exception as e:
            _LOGGER.warning(f"Failed to get power mode: {e}")

        _LOGGER.info(f"Coordinator update complete. Data keys: {list(data.keys())}")
        return data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="vizio_local",
        update_method=async_update_data,
        update_interval=timedelta(seconds=10),
    )

    await coordinator.async_refresh()

    hass.data[DOMAIN] = {
        "coordinator": coordinator,
        "vizio": vizio,
    }

    # Load platforms
    for platform in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(hass, platform, DOMAIN, {}, config)
        )

    return True
