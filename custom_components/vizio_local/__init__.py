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

        # Get picture settings
        for setting in ["backlight", "brightness", "contrast", "color", "tint", "sharpness"]:
            try:
                item = await vizio.get_setting("picture", setting, log_api_exception=False)
                if item:
                    # Handle both Item objects and raw values
                    if hasattr(item, 'value'):
                        data[f"picture_{setting}"] = item.value
                        data[f"picture_{setting}_hash"] = item.id
                    else:
                        data[f"picture_{setting}"] = item
                    _LOGGER.debug(f"Got picture {setting}: {data.get(f'picture_{setting}')}")
            except Exception as e:
                _LOGGER.warning(f"Failed to get picture {setting}: {e}")

        # Get audio settings
        for setting in ["volume", "mute"]:
            try:
                item = await vizio.get_setting("audio", setting, log_api_exception=False)
                if item:
                    # Handle both Item objects and raw values
                    if hasattr(item, 'value'):
                        data[f"audio_{setting}"] = item.value
                        data[f"audio_{setting}_hash"] = item.id
                    else:
                        data[f"audio_{setting}"] = item
                    _LOGGER.debug(f"Got audio {setting}: {data.get(f'audio_{setting}')}")
                else:
                    _LOGGER.warning(f"No data returned for audio {setting}")
            except Exception as e:
                _LOGGER.warning(f"Failed to get audio {setting}: {e}")

        # Get current input/app
        try:
            current_input = await vizio.get_current_input(log_api_exception=False)
            if current_input:
                data["current_source"] = current_input
                _LOGGER.debug(f"Current source: {current_input}")
        except Exception as e:
            _LOGGER.warning(f"Failed to get current input: {e}")

        # Get power state
        try:
            power_state = await vizio.get_power_state(log_api_exception=False)
            data["power_state"] = power_state
            _LOGGER.debug(f"Power state: {power_state}")
        except Exception as e:
            _LOGGER.warning(f"Failed to get power state: {e}")

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
